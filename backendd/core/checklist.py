import json
import re
import time
import logging
from core.query_engine import build_dual_engine, get_llm
from core.document_processor import get_constitutional_basis

logger = logging.getLogger(__name__)

# ── Pakistani constitutional article mapping ──────────────────────────
CONSTITUTIONAL_MAP = {
    "title"       : "Article 23 — Right to acquire and dispose of property",
    "noc"         : "Article 24 — Protection of property rights",
    "encumbrance" : "Article 24 — Protection of property rights",
    "co-owner"    : "Article 25 — Equality of citizens",
    "litigation"  : "Article 24 — Protection of property rights",
    "tax"         : "Article 23 — Right to acquire property subject to law",
    "inheritance" : "Article 23 — Right to acquire and dispose of property",
    "benami"      : "Article 24 — Protection against unlawful deprivation",
    "mutation"    : "Article 23 — Right to acquire and dispose of property",
}

# ── Red flag detection rules ──────────────────────────────────────────
RED_FLAG_RULES = [
    {
        "id"      : "RF001",
        "pattern" : ["no noc", "noc not", "noc missing", "without noc"],
        "label"   : "Missing NOC",
        "statute" : "LDA/CDA/RDA Bye-Laws",
        "article" : "Article 24 — Protection of property rights",
    },
    {
        "id"      : "RF002",
        "pattern" : ["price differ", "amount differ", "consideration differ",
                     "inconsistent price", "discrepan"],
        "label"   : "Sale price discrepancy across documents",
        "statute" : "Registration Act 1908, Section 17",
        "article" : "Article 23 — Right to acquire property subject to law",
    },
    {
        "id"      : "RF003",
        "pattern" : ["litigation", "court order", "injunction", "caveat",
                     "suit pending", "legal dispute"],
        "label"   : "Undisclosed litigation or court order",
        "statute" : "Transfer of Property Act 1882, Section 52",
        "article" : "Article 24 — Protection of property rights",
    },
    {
        "id"      : "RF004",
        "pattern" : ["co-owner", "co owner", "joint owner", "heir",
                     "without consent", "other owner"],
        "label"   : "Third-party or co-owner interest without consent",
        "statute" : "Muslim Family Laws Ordinance 1961",
        "article" : "Article 25 — Equality of citizens",
    },
    {
        "id"      : "RF005",
        "pattern" : ["cnic mismatch", "cnic differ", "id differ",
                     "identity differ", "name differ"],
        "label"   : "CNIC mismatch across documents",
        "statute" : "Registration Act 1908, Section 17",
        "article" : "Article 23 — Right to acquire property subject to law",
    },
    {
        "id"      : "RF006",
        "pattern" : ["benami", "benamidar", "beneficial owner",
                     "on behalf of", "nominee"],
        "label"   : "Potential Benami transaction",
        "statute" : "Benami Transactions (Prohibition) Act 2017",
        "article" : "Article 24 — Protection of property rights",
    },
    {
        "id"      : "RF007",
        "pattern" : ["no mutation", "mutation missing", "no intiqal",
                     "intiqal not", "no registry"],
        "label"   : "Missing mutation (Intiqal) record",
        "statute" : "Land Revenue Act 1967",
        "article" : "Article 23 — Right to acquire and dispose of property",
    },
]

# ── Property due diligence checklist ─────────────────────────────────
PROPERTY_CHECKLIST = [
    {
        "id": 1,
        "question": (
            "Is the title deed present and registered in the name of the vendor? "
            "Verify Registry number, Sub-Registrar office, and registration date."
        ),
        "topic": "title",
    },
    {
        "id": 2,
        "question": (
            "Is the property free from all encumbrances, mortgages, charges, "
            "or liens? Check for any bank charges or third-party claims."
        ),
        "topic": "encumbrance",
    },
    {
        "id": 3,
        "question": (
            "Are all required NOCs present — from LDA/CDA/RDA/TMA and all "
            "relevant local authorities? Identify which authority issued each NOC."
        ),
        "topic": "noc",
    },
    {
        "id": 4,
        "question": (
            "Are the property boundaries, Khasra number, Khata number, and "
            "area measurements consistent across all submitted documents?"
        ),
        "topic": "boundaries",
    },
    {
        "id": 5,
        "question": (
            "Is there any ongoing or threatened litigation, court order, "
            "injunction, or caveat against the property or the vendor?"
        ),
        "topic": "litigation",
    },
    {
        "id": 6,
        "question": (
            "Is the sale consideration consistent across all documents? "
            "Is it supported by bank evidence, pay orders, or payment receipts?"
        ),
        "topic": "consideration",
    },
    {
        "id": 7,
        "question": (
            "Are all signatures, attestations, thumb impressions, and "
            "notarial certifications present and valid on all documents?"
        ),
        "topic": "attestation",
    },
    {
        "id": 8,
        "question": (
            "Is the land use classification consistent with the intended "
            "purpose of acquisition? Check for residential, commercial, or "
            "agricultural zoning."
        ),
        "topic": "land_use",
    },
    {
        "id": 9,
        "question": (
            "Are utility connections — electricity, gas, water, PTCL — "
            "documented and registered in the vendor's name? "
            "Are there any outstanding utility dues?"
        ),
        "topic": "utilities",
    },
    {
        "id": 10,
        "question": (
            "Are all outstanding property taxes, withholding taxes under "
            "Sections 236C and 236K of the Income Tax Ordinance 2001, "
            "CVT, and stamp duty arrears disclosed and settled?"
        ),
        "topic": "tax",
    },
    {
        "id": 11,
        "question": (
            "Is the vendor's CNIC number verified and consistent across "
            "all transaction documents including the sale deed, NOC, and "
            "utility bills?"
        ),
        "topic": "cnic",
    },
    {
        "id": 12,
        "question": (
            "Are there any co-owners, inherited co-sharers, legal heirs, "
            "or third-party interests in the property? If so, is their "
            "written consent to the transfer documented?"
        ),
        "topic": "co-owner",
    },
    {
        "id": 13,
        "question": (
            "Is the possession transfer date, handover mechanism, and "
            "physical possession status explicitly documented?"
        ),
        "topic": "possession",
    },
    {
        "id": 14,
        "question": (
            "Are all conditions precedent to the transfer clearly identified "
            "and confirmed as satisfied? List any outstanding conditions."
        ),
        "topic": "conditions",
    },
    {
        "id": 15,
        "question": (
            "Is there a registered mutation (Intiqal) on record from LRMIS? "
            "Is the Fard-e-Malkiat consistent with the Registry? "
            "Is the transfer mode legally valid under Pakistani land revenue law?"
        ),
        "topic": "mutation",
    },
]

LOAN_CHECKLIST = [
    {
        "id": 1,
        "question": (
            "Is the loan agreement present and duly executed by all parties? "
            "Verify signatures, date, and notarial attestation."
        ),
        "topic": "title",
    },
    {
        "id": 2,
        "question": (
            "Is the mortgage deed or charge document registered with the "
            "relevant Sub-Registrar under Section 17 of the Registration "
            "Act 1908? Verify registration number and date."
        ),
        "topic": "encumbrance",
    },
    {
        "id": 3,
        "question": (
            "Is the security property free from all prior encumbrances, "
            "charges, or liens? Has a search been conducted at the "
            "Sub-Registrar's office?"
        ),
        "topic": "encumbrance",
    },
    {
        "id": 4,
        "question": (
            "Is the title of the mortgagor to the security property clear "
            "and marketable? Are all title documents present and consistent?"
        ),
        "topic": "title",
    },
    {
        "id": 5,
        "question": (
            "Is the loan amount, interest rate, repayment schedule, and "
            "penalty clause clearly specified and consistent across all "
            "documents?"
        ),
        "topic": "consideration",
    },
    {
        "id": 6,
        "question": (
            "Are the State Bank of Pakistan prudential regulations complied "
            "with? Is the debt-to-equity ratio and exposure limit within "
            "permissible limits?"
        ),
        "topic": "tax",
    },
    {
        "id": 7,
        "question": (
            "Is the borrower's CNIC verified and consistent across all "
            "loan documents? Is the borrower an active FBR filer?"
        ),
        "topic": "cnic",
    },
    {
        "id": 8,
        "question": (
            "Is a valuation report for the security property present and "
            "prepared by a SECP-approved valuer? Does it support the "
            "loan-to-value ratio?"
        ),
        "topic": "boundaries",
    },
    {
        "id": 9,
        "question": (
            "Is an insurance policy on the security property present and "
            "assigned in favour of the lending institution?"
        ),
        "topic": "utilities",
    },
    {
        "id": 10,
        "question": (
            "Are all NOCs from relevant authorities present for the "
            "security property? Is the property free from any government "
            "acquisition notice?"
        ),
        "topic": "noc",
    },
    {
        "id": 11,
        "question": (
            "Is there any ongoing litigation, court order, or injunction "
            "against the borrower or the security property?"
        ),
        "topic": "litigation",
    },
    {
        "id": 12,
        "question": (
            "Are the disbursement conditions clearly specified? Has the "
            "borrower satisfied all conditions precedent to disbursement?"
        ),
        "topic": "conditions",
    },
    {
        "id": 13,
        "question": (
            "Is the personal guarantee or corporate guarantee present and "
            "executed? Is the guarantor's financial capacity documented?"
        ),
        "topic": "attestation",
    },
    {
        "id": 14,
        "question": (
            "Are withholding tax obligations under the Income Tax Ordinance "
            "2001 on loan interest payments documented and complied with?"
        ),
        "topic": "tax",
    },
    {
        "id": 15,
        "question": (
            "Is the registered mutation (Intiqal) of the security property "
            "consistent with the title documents? Is the Fard-e-Malkiat "
            "attached and verified?"
        ),
        "topic": "mutation",
    },
]

ACQUISITION_CHECKLIST = [
    {
        "id": 1,
        "question": (
            "Is the Share Purchase Agreement or Asset Purchase Agreement "
            "present and duly executed by authorised signatories of both parties?"
        ),
        "topic": "title",
    },
    {
        "id": 2,
        "question": (
            "Is the target company duly incorporated under the Companies "
            "Act 2017? Are the Certificate of Incorporation, Memorandum, "
            "and Articles of Association present?"
        ),
        "topic": "attestation",
    },
    {
        "id": 3,
        "question": (
            "Are all SECP filings current and compliant? Are annual returns, "
            "Form-A, Form-29, and audited financial statements filed and "
            "up to date?"
        ),
        "topic": "noc",
    },
    {
        "id": 4,
        "question": (
            "Is the share register present and consistent with the SECP "
            "record? Are all share transfers properly executed and stamped?"
        ),
        "topic": "title",
    },
    {
        "id": 5,
        "question": (
            "Are there any encumbrances, charges, or pledges over the "
            "shares or assets of the target company registered with SECP?"
        ),
        "topic": "encumbrance",
    },
    {
        "id": 6,
        "question": (
            "Is the consideration amount consistent across all transaction "
            "documents? Is it supported by board resolutions and shareholder "
            "approvals?"
        ),
        "topic": "consideration",
    },
    {
        "id": 7,
        "question": (
            "Are there any pending or threatened litigation, arbitration, "
            "regulatory proceedings, or tax disputes involving the target "
            "company?"
        ),
        "topic": "litigation",
    },
    {
        "id": 8,
        "question": (
            "Are all material contracts, licences, and permits of the target "
            "company present? Do they contain change-of-control clauses "
            "that require counterparty consent?"
        ),
        "topic": "conditions",
    },
    {
        "id": 9,
        "question": (
            "Are all outstanding tax liabilities — income tax, sales tax, "
            "withholding tax — of the target company disclosed and quantified? "
            "Are FBR tax clearance certificates present?"
        ),
        "topic": "tax",
    },
    {
        "id": 10,
        "question": (
            "Are all employee-related liabilities — provident fund, EOBI, "
            "SESSI, gratuity — disclosed and adequately provided for?"
        ),
        "topic": "utilities",
    },
    {
        "id": 11,
        "question": (
            "Is the Competition Commission of Pakistan (CCP) merger filing "
            "required? If so, has prior approval been obtained?"
        ),
        "topic": "noc",
    },
    {
        "id": 12,
        "question": (
            "Are the CNICs of all directors and major shareholders verified "
            "and consistent with SECP records?"
        ),
        "topic": "cnic",
    },
    {
        "id": 13,
        "question": (
            "Are all representations and warranties in the acquisition "
            "agreement adequately supported by the disclosed documents?"
        ),
        "topic": "attestation",
    },
    {
        "id": 14,
        "question": (
            "Are all conditions precedent to closing satisfied or waived? "
            "List any outstanding closing conditions."
        ),
        "topic": "conditions",
    },
    {
        "id": 15,
        "question": (
            "Is the Anti-Money Laundering Act 2010 compliance documented? "
            "Is the source of acquisition funds clearly established and "
            "supported by bank evidence?"
        ),
        "topic": "aml",
    },
]

CHECKLISTS = {
    "property"    : PROPERTY_CHECKLIST,
    "loan"        : LOAN_CHECKLIST,
    "acquisition" : ACQUISITION_CHECKLIST,
}


def _parse_llm_response(raw: str, question_item: dict) -> dict:
    """
    Parse LLM response into structured finding.
    Falls back gracefully if JSON is malformed.
    """
    try:
        # Strip markdown code fences if present
        # Strip thinking tokens from reasoning models (e.g. Qwen, DeepSeek)
        clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        # Strip markdown code fences
        clean = re.sub(r"```(?:json)?", "", clean).strip()
        # Strip any trailing backticks or stray characters
        clean = clean.replace("`", "").strip()
        data = json.loads(clean)
        # Inject constitutional basis if not provided
        if not data.get("constitutional_basis"):
            data["constitutional_basis"] = get_constitutional_basis(
                question_item["topic"]
            )
        return data
    except json.JSONDecodeError:
        logger.warning(f"JSON parse failed for Q{question_item['id']} — using fallback")
        return {
            "question_id"          : question_item["id"],
            "question"             : question_item["question"],
            "finding"              : raw[:500] if raw else "No response received.",
            "reasoning"            : "Could not parse structured response.",
            "document_citation"    : "See raw response",
            "statutory_citation"   : "N/A",
            "constitutional_basis" : get_constitutional_basis(question_item["topic"]),
            "risk_level"           : "MEDIUM",
            "recommendation"       : "Manual review required for this item.",
            "missing_documents"    : [],
            "query_source"         : "checklist",
        }


def detect_red_flags(findings: list[dict]) -> list[dict]:
    """
    Scan all findings for red flag patterns.
    Returns list of triggered red flag objects.
    """
    triggered = []
    all_text = " ".join(
        (f.get("finding", "") + " " + f.get("reasoning", "")).lower()
        for f in findings
    )
    for rule in RED_FLAG_RULES:
        if any(p in all_text for p in rule["pattern"]):
            triggered.append(rule)
    return triggered


def run_checklist(
    session_index,
    legal_corpus_index,
    transaction_type: str = "property",
    flags: dict = None,
) -> dict:
    """
    Run the full due diligence checklist against both indexes.
    Returns structured results including findings and red flags.
    """
    flags = flags or {}
    checklist = CHECKLISTS.get(transaction_type, PROPERTY_CHECKLIST)

    # Add supplementary questions based on detected flags
    supplementary = []
    if flags.get("is_inherited"):
        supplementary.append({
            "id"      : 16,
            "question": (
                "This appears to be an inherited property. "
                "Is a succession certificate present? "
                "Are legal heirship certificates from a competent court available? "
                "Have all legal heirs consented to the transfer in writing "
                "as required under the Muslim Family Laws Ordinance 1961?"
            ),
            "topic": "inheritance",
        })
    if flags.get("benami_risk"):
        supplementary.append({
            "id"      : 17,
            "question": (
                "Potential benami indicators detected. "
                "Is the sale consideration being paid by the named buyer themselves? "
                "Is there any undisclosed beneficial owner or third-party financier? "
                "Assess compliance with the Benami Transactions "
                "(Prohibition) Act 2017."
            ),
            "topic": "benami",
        })
    if flags.get("housing_society"):
        society = flags["housing_society"]
        supplementary.append({
            "id"      : 19,
            "question": (
                f"This transaction involves {society}. "
                f"Are all society-specific transfer documents present — "
                f"including the transfer letter, NOC from the society, "
                f"dues clearance certificate, and membership transfer "
                f"confirmation? Are there any outstanding charges payable "
                f"to {society} before transfer can be completed?"
            ),
            "topic": "housing_society",
        })
    if flags.get("aml_threshold"):
        supplementary.append({
            "id"      : 18,
            "question": (
                "Transaction value exceeds PKR 10,000,000. "
                "Is the source of funds documented? "
                "Are enhanced due diligence requirements under the "
                "Anti-Money Laundering Act 2010 and SECP AML/CFT "
                "Regulations 2018 satisfied?"
            ),
            "topic": "aml",
        })

    full_checklist = checklist + supplementary

    findings = []
    logger.info(f"Running {len(full_checklist)} checklist questions...")

    for item in full_checklist:
        logger.info(f"  Q{item['id']}: {item['question'][:60]}...")
        try:
            time.sleep(4)   # Respect Groq free tier 12K TPM limit
            # Fresh engine per question — prevents context accumulation
            dual_engine = build_dual_engine(session_index, legal_corpus_index)
            response = dual_engine.query(item["question"])
            raw = str(response)
            finding = _parse_llm_response(raw, item)
            finding["question_id"] = item["id"]
            finding["query_source"] = "checklist"
            findings.append(finding)
        except Exception as e:
            logger.error(f"  Q{item['id']} failed: {e}")
            findings.append(_parse_llm_response("", item))

    red_flags = detect_red_flags(findings)
    high_risk  = [f for f in findings if f.get("risk_level") == "HIGH"]
    med_risk   = [f for f in findings if f.get("risk_level") == "MEDIUM"]

    return {
        "transaction_type" : transaction_type,
        "total_questions"  : len(full_checklist),
        "findings"         : findings,
        "red_flags"        : red_flags,
        "high_risk_count"  : len(high_risk),
        "medium_risk_count": len(med_risk),
        "low_risk_count"   : len(findings) - len(high_risk) - len(med_risk),
        "flags"            : flags,
    }


def run_freeform_query(
    question: str,
    session_index,
    legal_corpus_index,
) -> dict:
    """
    Handle a free-form legal question from the lawyer.
    """
    time.sleep(2)
    dual_engine = build_dual_engine(session_index, legal_corpus_index)
    try:
        response = dual_engine.query(question)
        raw = str(response)
        finding = _parse_llm_response(
            raw,
            {"id": 0, "question": question, "topic": "general"},
        )
        finding["query_source"] = "freeform"
        return finding
    except Exception as e:
        logger.error(f"Free-form query failed: {e}")
        return {
            "question_id"          : 0,
            "question"             : question,
            "finding"              : f"Query failed: {str(e)}",
            "reasoning"            : "",
            "document_citation"    : "",
            "statutory_citation"   : "",
            "constitutional_basis" : "",
            "risk_level"           : "MEDIUM",
            "recommendation"       : "Please retry or rephrase your question.",
            "missing_documents"    : [],
            "query_source"         : "freeform",
        }