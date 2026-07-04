import { Component } from "react"

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: "100vh",
          background: "#070b14",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "2rem",
        }}>
          <div style={{
            background: "rgba(255,95,95,0.08)",
            border: "1px solid rgba(255,95,95,0.3)",
            borderRadius: "14px",
            padding: "2.5rem",
            maxWidth: "520px",
            textAlign: "center",
            color: "#ff5f5f",
          }}>
            <div style={{ fontSize: "2.5rem", marginBottom: "1rem" }}>⚠️</div>
            <h2 style={{ marginBottom: "0.8rem", color: "#eef0f6" }}>
              Something went wrong
            </h2>
            <p style={{ fontSize: "0.88rem", color: "#8892a4",
              marginBottom: "1.5rem" }}>
              {this.state.error?.message || "An unexpected error occurred."}
            </p>
            <button
              onClick={() => window.location.reload()}
              style={{
                padding: "0.8rem 2rem",
                background: "linear-gradient(135deg, #c9a84c, #e8c96a)",
                color: "#0a0e1a",
                border: "none",
                borderRadius: "8px",
                fontWeight: "700",
                cursor: "pointer",
                fontSize: "0.9rem",
              }}
            >
              Reload Application
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}