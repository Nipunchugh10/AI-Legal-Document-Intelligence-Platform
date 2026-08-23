import React, { useState } from "react";
import { useAuthStore } from "../store/useAuthStore";

interface ActivityItem {
  id: number;
  action: string;
  category: "analysis" | "security" | "upload" | "session";
  timestamp: string;
  details: string;
}

export const HistoryPage: React.FC = () => {
  const user = useAuthStore((state) => state.user);
  const [filterCategory, setFilterCategory] = useState<string>("all");

  const sampleActivities: ActivityItem[] = [
    {
      id: 1,
      action: "Multi-Agent Dialectic Analysis Completed",
      category: "analysis",
      timestamp: "Today at 09:42 AM",
      details: "Ran 5-agent LangGraph workflow with 8-domain statutory benchmarks.",
    },
    {
      id: 2,
      action: "Contract Ingested & Embedded",
      category: "upload",
      timestamp: "Today at 09:40 AM",
      details: "Extracted clauses and stored 768-dim vectors in ChromaDB vector store.",
    },
    {
      id: 3,
      action: "Two-Factor Authentication Verified",
      category: "security",
      timestamp: "Today at 09:30 AM",
      details: "Verified 6-digit Email OTP with SHA-256 cryptographic check.",
    },
    {
      id: 4,
      action: "Secure Session Created",
      category: "session",
      timestamp: "Today at 09:30 AM",
      details: "Issued refresh token with 40-minute inactivity auto-logout tracking.",
    },
  ];

  const filtered =
    filterCategory === "all"
      ? sampleActivities
      : sampleActivities.filter((a) => a.category === filterCategory);

  return (
    <div className="placeholder-view-container">
      {/* Hero Card */}
      <div className="placeholder-hero-card">
        <div className="placeholder-badge">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <polyline points="12 6 12 12 16 14" />
          </svg>
          Immutable Legal Audit Trail
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <h1 className="placeholder-title">Activity Timeline & Audit Trail</h1>
            <p className="placeholder-desc">
              Every document ingestion, analysis execution, Q&A inquiry, and security verification is
              timestamped and permanently recorded for compliance and accountability.
            </p>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => alert("Audit log export formatted as JSON/PDF will be generated.")}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export Compliance Audit Log
          </button>
        </div>

        {/* Filter Pills */}
        <div style={{ display: "flex", gap: "8px", marginTop: "12px", flexWrap: "wrap" }}>
          {[
            { id: "all", label: "All Activity" },
            { id: "analysis", label: "Analyses & Redlines" },
            { id: "upload", label: "Document Ingestions" },
            { id: "security", label: "2FA & Auth" },
            { id: "session", label: "Active Sessions" },
          ].map((f) => (
            <button
              key={f.id}
              onClick={() => setFilterCategory(f.id)}
              style={{
                padding: "6px 14px",
                borderRadius: "9999px",
                border: "1px solid var(--color-border)",
                background: filterCategory === f.id ? "rgba(92, 98, 236, 0.2)" : "rgba(255, 255, 255, 0.02)",
                color: filterCategory === f.id ? "var(--color-primary)" : "var(--color-text-muted)",
                fontSize: "0.82rem",
                fontWeight: filterCategory === f.id ? "600" : "500",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Activity Timeline List */}
      <div className="glass-panel" style={{ padding: "24px", borderRadius: "16px" }}>
        <h3 style={{ fontSize: "1.15rem", fontWeight: "600", marginBottom: "20px" }}>
          Recent Audit Events ({user?.email})
        </h3>

        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {filtered.map((item) => (
            <div
              key={item.id}
              style={{
                display: "flex",
                gap: "16px",
                padding: "16px",
                borderRadius: "12px",
                background: "rgba(255, 255, 255, 0.02)",
                border: "1px solid var(--color-border)",
                alignItems: "flex-start",
              }}
            >
              <div
                style={{
                  width: "36px",
                  height: "36px",
                  borderRadius: "8px",
                  background:
                    item.category === "analysis"
                      ? "rgba(92, 98, 236, 0.15)"
                      : item.category === "security"
                      ? "rgba(16, 185, 129, 0.15)"
                      : "rgba(56, 189, 248, 0.15)",
                  color:
                    item.category === "analysis"
                      ? "var(--color-primary)"
                      : item.category === "security"
                      ? "var(--color-success)"
                      : "var(--color-accent)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ fontSize: "0.95rem" }}>{item.action}</strong>
                  <span style={{ fontSize: "0.78rem", color: "var(--color-text-muted)" }}>{item.timestamp}</span>
                </div>
                <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", marginTop: "4px", margin: "4px 0 0 0" }}>
                  {item.details}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
