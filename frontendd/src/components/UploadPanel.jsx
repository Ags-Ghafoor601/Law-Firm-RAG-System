import { useState, useRef } from "react"
import axios from "axios"
import API_BASE from "../config"

const CITIES = ["islamabad", "rawalpindi", "lahore", "karachi"]
const TYPES  = ["property", "loan", "acquisition"]
const SOCIETIES = ["None", "DHA Islamabad", "DHA Lahore",
                   "Bahria Town Rawalpindi", "Bahria Town Lahore"]
const FIRM_PROFILES = {
  "josh_mak": {
    name: "Josh and Mak International",
    address: "No. 01, LG Floor, Josh and Mak International, Park Avenue, Hamza Rd, F-11/1, Islamabad, 44000",
    phone: "+92-304-8734889",
    email: "aemen@joshandmak.com",
    tagline: "Advocates & Legal Consultants — Legal 500 Ranked",
  },
  "mumtaz_brohi": {
    name: "Mumtaz & Brohi",
    address: "House No. 134, Street No. 60, Sector I-8/3, Islamabad",
    phone: "+92-51-4800851",
    email: "info@mumtazandbrohi.com",
    tagline: "Barristers & Corporate Counsel — Legal 500 Ranked",
  },
  "custom": {
    name: "", address: "", phone: "", email: "", tagline: "",
  },
}

export default function UploadPanel({ onSessionStart }) {
  const [files, setFiles]            = useState([])
  const [transactionType, setType]   = useState("property")
  const [city, setCity]              = useState("islamabad")
  const [society, setSociety]        = useState("None")
  const [firmProfile, setFirmProfile]= useState("custom")
  const [firmName, setFirmName]      = useState("")
  const [firmAddress, setFirmAddress]= useState("")
  const [firmPhone, setFirmPhone]    = useState("")
  const [firmEmail, setFirmEmail]    = useState("")
  const [firmTagline, setFirmTagline]= useState("")
  const [loading, setLoading]        = useState(false)
  const [error, setError]            = useState(null)
  const [dragging, setDragging]      = useState(false)
  const inputRef                     = useRef(null)

  function handleFirmProfileChange(profileKey) {
    setFirmProfile(profileKey)
    const p = FIRM_PROFILES[profileKey]
    if (p) {
      setFirmName(p.name)
      setFirmAddress(p.address)
      setFirmPhone(p.phone)
      setFirmEmail(p.email)
      setFirmTagline(p.tagline)
    }
  }

  function handleFiles(fileList) {
    const pdfs = [...fileList].filter(f => f.name.toLowerCase().endsWith(".pdf"))
    if (pdfs.length !== fileList.length) {
      setError("Only PDF files are accepted.")
    } else {
      setError(null)
    }
    setFiles(pdfs)
  }

  async function handleSubmit() {
    if (!files.length) return setError("Please select at least one PDF.")
    setLoading(true)
    setError(null)
    const form = new FormData()
    files.forEach(f => form.append("files", f))
    form.append("transaction_type", transactionType)
    form.append("city", city)
    form.append("housing_society", society === "None" ? "" : society)
    form.append("firm_name", firmName || "Law Firm")
    form.append("firm_address", firmAddress)
    form.append("firm_phone", firmPhone)
    form.append("firm_email", firmEmail)
    form.append("firm_tagline", firmTagline)
    try {
      const res = await axios.post(`${API_BASE}/api/upload`, form)
      onSessionStart(res.data.session_id)
    } catch (e) {
      setError(e.response?.data?.detail || "Upload failed. Is the backend running?")
    } finally {
      setLoading(false)
    }
  }

  const capitalize = s => s.charAt(0).toUpperCase() + s.slice(1)

  return (
    <div className="panel upload-panel">
      <h2>Upload Legal Documents</h2>
      <p className="panel-subtitle">
        Upload your PDF bundle and configure the review parameters below.
        The system will run a full due diligence analysis against Pakistani statutes.
      </p>
      {/* Firm customisation */}
      <div className="field-group">
        <label className="field-label">Law Firm Profile</label>
        <select
          value={firmProfile}
          onChange={e => handleFirmProfileChange(e.target.value)}
        >
          <option value="custom">Custom / Enter Manually</option>
          <option value="josh_mak">Josh and Mak International (Islamabad)</option>
          <option value="mumtaz_brohi">Mumtaz & Brohi (Islamabad)</option>
        </select>
      </div>

      <div className="firm-fields">
        <div className="field-group">
          <label className="field-label">Firm Name</label>
          <input
            type="text"
            className="text-input"
            placeholder="e.g. Rana Ijaz & Partners"
            value={firmName}
            onChange={e => setFirmName(e.target.value)}
          />
        </div>
        <div className="field-row">
          <div className="field-group">
            <label className="field-label">Phone</label>
            <input
              type="text"
              className="text-input"
              placeholder="+92-51-XXXXXXX"
              value={firmPhone}
              onChange={e => setFirmPhone(e.target.value)}
            />
          </div>
          <div className="field-group">
            <label className="field-label">Email</label>
            <input
              type="text"
              className="text-input"
              placeholder="info@firm.com"
              value={firmEmail}
              onChange={e => setFirmEmail(e.target.value)}
            />
          </div>
        </div>
        <div className="field-group">
          <label className="field-label">Address</label>
          <input
            type="text"
            className="text-input"
            placeholder="Chamber No., Street, City"
            value={firmAddress}
            onChange={e => setFirmAddress(e.target.value)}
          />
        </div>
        <div className="field-group">
          <label className="field-label">Tagline (appears on memo)</label>
          <input
            type="text"
            className="text-input"
            placeholder="Advocates & Legal Consultants"
            value={firmTagline}
            onChange={e => setFirmTagline(e.target.value)}
          />
        </div>
      </div>
      <div className="field-row">
        <div className="field-group">
          <label className="field-label">Transaction Type</label>
          <select value={transactionType} onChange={e => setType(e.target.value)}>
            {TYPES.map(t => (
              <option key={t} value={t}>{capitalize(t)}</option>
            ))}
          </select>
        </div>
        <div className="field-group">
          <label className="field-label">City / Authority</label>
          <select value={city} onChange={e => setCity(e.target.value)}>
            {CITIES.map(c => (
              <option key={c} value={c}>{capitalize(c)}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="field-group">
        <label className="field-label">Housing Society (Optional)</label>
        <select value={society} onChange={e => setSociety(e.target.value)}>
          {SOCIETIES.map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="field-group">
        <label className="field-label">PDF Documents</label>
        <div
          className={`upload-zone ${dragging ? "dragging" : ""}`}
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={e => {
            e.preventDefault()
            setDragging(false)
            handleFiles(e.dataTransfer.files)
          }}
          onClick={() => inputRef.current?.click()}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            multiple
            style={{ display: "none" }}
            onChange={e => handleFiles(e.target.files)}
          />
          <div className="upload-icon">📎</div>
          <h3>
            {dragging
              ? "Drop files here"
              : <>Drag & drop PDFs or <span className="browse-link">browse</ span></>
            }
          </h3>
          <p>Supports text-based and scanned PDFs · Urdu + English · Multiple files</p>
        </div>

        {files.length > 0 && (
          <div className="file-list">
            {files.map((f, i) => (
              <div key={i} className="file-item">
                <span className="file-item-icon">📄</span>
                <span>{f.name}</span>
                <span style={{ marginLeft: "auto", color: "var(--gray-600)", fontSize: "0.78rem" }}>
                  {(f.size / 1024).toFixed(0)} KB
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {error && <div className="error">⚠️ {error}</div>}

      <button
        className="primary-btn"
        onClick={handleSubmit}
        disabled={loading || !files.length}
      >
        {loading
          ? <><span>⏳</span> Uploading...</>
          : <><span>🔍</span> Run Due Diligence Review</>
        }
      </button>
    </div>
  )
}