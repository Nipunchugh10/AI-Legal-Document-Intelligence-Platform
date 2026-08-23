import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";

interface AnalysisResult {
  id: number;
  contract_id: number;
  analysis_type: string;
  result_json: {
    document_summary?: string;
    key_entities?: string[];
    governing_law?: string;
    clauses?: Array<{ clause_type: string; text: string; confidence?: number }>;
    risks?: Array<{
      risk_type: string;
      severity: "RED_FLAG" | "YELLOW_FLAG" | "GREEN_FLAG" | "HIGH" | "MEDIUM" | "LOW";
      explanation: string;
      flagged_text: string;
      suggested_revision?: string;
      negotiation_tip?: string;
    }>;
    compliance_issues?: Array<{
      statute: string;
      issue: string;
      severity: string;
      recommendation: string;
    }>;
    executive_summary?: string;
  };
  created_at: string;
}

interface ContractInfo {
  id: number;
  filename: string;
  upload_path: string;
  status: string;
  created_at: string;
}

export const ContractDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [contract, setContract] = useState<ContractInfo | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState<"overview" | "risks" | "clauses" | "compliance" | "negotiation">("overview");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fetchContractData = async () => {
    if (!id) return;
    setIsLoading(true);
    setErrorMsg(null);
    try {
      // 1. Fetch contract metadata
      const contractRes = await api.get<ContractInfo>(`/contracts/${id}`);
      setContract(contractRes.data);

      // 2. Try fetching existing analysis
      try {
        const analysisRes = await api.get<AnalysisResult>(`/contracts/${id}/analysis`);
        setAnalysis(analysisRes.data);
      } catch (analysisErr) {
        // Analysis might not have run yet, which is fine
        setAnalysis(null);
      }
    } catch (err: any) {
      setErrorMsg("Failed to load contract details.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchContractData();
  }, [id]);

  const handleRunAnalysis = async () => {
    if (!id) return;
    setIsAnalyzing(true);
    setErrorMsg(null);
    try {
      const response = await api.post(`/contracts/${id}/analyze`);
      setAnalysis({
        id: 0,
        contract_id: Number(id),
        analysis_type: "complete_workflow",
        result_json: response.data,
        created_at: new Date().toISOString(),
      });
      // Refresh contract status
      fetchContractData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Analysis execution failed. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="page-loader" style={{ minHeight: "60vh" }}>
        <div className="spinner" />
        <p className="loader-text">Loading contract workspace...</p>
      </div>
    );
  }

  if (!contract) {
    return (
      <div className="placeholder-hero-card">
        <h2>Contract Not Found</h2>
        <p>The requested contract could not be located in your vault.</p>
        <button className="btn btn-primary" onClick={() => navigate("/dashboard")}>
          Return to Vault
        </button>
      </div>
    );
  }

  return (
    <div className="placeholder-view-container">
      {/* Header bar */}
      <div className="placeholder-hero-card" style={{ padding: "24px 32px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "16px" }}>
          <div>
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
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              Contract Analysis Workspace
            </div>
            <h1 style={{ fontSize: "1.6rem", marginTop: "8px", fontWeight: "700" }}>
              {contract.filename}
            </h1>
            <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
              Uploaded on {new Date(contract.created_at).toLocaleDateString()} • Status:{" "}
              <strong style={{ color: "var(--color-primary)" }}>{contract.status.toUpperCase()}</strong>
            </p>
          </div>

          <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
            <button
              className="btn btn-secondary"
              onClick={() => navigate(`/contracts/${id}/ask`)}
            >
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
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <span>Ask Questions</span>
            </button>

            <button
              className="btn btn-primary"
              onClick={handleRunAnalysis}
              disabled={isAnalyzing}
            >
              {isAnalyzing ? (
                <>
                  <div className="spinner spinner-sm" />
                  <span>Analyzing Multi-Agent Dialectic...</span>
                </>
              ) : (
                <>
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
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  <span>{analysis ? "Re-Run Complete Analysis" : "Run AI Legal Analysis"}</span>
                </>
              )}
            </button>
          </div>
        </div>

        {errorMsg && <div className="alert alert-danger" style={{ marginTop: "16px" }}>{errorMsg}</div>}
      </div>

      {/* Two-Panel Layout */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr", gap: "24px", alignItems: "start" }}>
        {/* Left Panel: Document Metadata & Navigator */}
        <div className="glass-panel" style={{ padding: "24px", borderRadius: "16px" }}>
          <h3 style={{ fontSize: "1.15rem", fontWeight: "600", marginBottom: "16px" }}>
            Document Overview
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: "12px", fontSize: "0.9rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Document Name</span>
              <span style={{ fontWeight: "600" }}>{contract.filename}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Analysis State</span>
              <span style={{ color: "var(--color-success)", fontWeight: "600" }}>{contract.status}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid var(--color-border)", paddingBottom: "8px" }}>
              <span style={{ color: "var(--color-text-muted)" }}>Upload Date</span>
              <span>{new Date(contract.created_at).toLocaleDateString()}</span>
            </div>
          </div>

          <div style={{ marginTop: "24px", padding: "16px", background: "rgba(255, 255, 255, 0.02)", borderRadius: "10px", border: "1px solid var(--color-border)" }}>
            <h4 style={{ fontSize: "0.95rem", fontWeight: "600", marginBottom: "8px" }}>
              AI Intelligence Pipeline Ready
            </h4>
            <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", lineHeight: "1.5" }}>
              Full interactive document viewer with clause highlight jumping, IRAC legal citations, and 8-domain statutory codes is integrated in Day 34–35.
            </p>
          </div>
        </div>

        {/* Right Panel: Analysis Workspace Tabs */}
        <div className="glass-panel" style={{ padding: "24px", borderRadius: "16px" }}>
          {/* Tab Navigation */}
          <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid var(--color-border)", paddingBottom: "12px", marginBottom: "20px", overflowX: "auto" }}>
            {(["overview", "risks", "clauses", "compliance", "negotiation"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  padding: "8px 14px",
                  borderRadius: "8px",
                  border: "none",
                  background: activeTab === tab ? "rgba(92, 98, 236, 0.2)" : "transparent",
                  color: activeTab === tab ? "var(--color-primary)" : "var(--color-text-muted)",
                  fontWeight: activeTab === tab ? "600" : "500",
                  cursor: "pointer",
                  fontSize: "0.88rem",
                  textTransform: "capitalize",
                }}
              >
                {tab === "risks" ? "3-Tier Risks" : tab === "negotiation" ? "Redlines" : tab}
              </button>
            ))}
          </div>

          {/* Tab Contents */}
          {analysis ? (
            <div>
              {activeTab === "overview" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <h4 style={{ fontSize: "1.1rem", fontWeight: "600" }}>Executive Summary</h4>
                  <p style={{ fontSize: "0.92rem", lineHeight: "1.6", color: "var(--color-text-main)" }}>
                    {analysis.result_json.executive_summary || analysis.result_json.document_summary || "Analysis report generated successfully."}
                  </p>
                </div>
              )}

              {activeTab === "risks" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                  <h4 style={{ fontSize: "1.1rem", fontWeight: "600" }}>Traffic Light Risk Flags</h4>
                  {analysis.result_json.risks && analysis.result_json.risks.length > 0 ? (
                    analysis.result_json.risks.map((risk, i) => (
                      <div
                        key={i}
                        style={{
                          padding: "16px",
                          borderRadius: "10px",
                          border: "1px solid var(--color-border)",
                          background:
                            risk.severity === "RED_FLAG" || risk.severity === "HIGH"
                              ? "rgba(244, 63, 94, 0.08)"
                              : risk.severity === "YELLOW_FLAG" || risk.severity === "MEDIUM"
                              ? "rgba(245, 158, 11, 0.08)"
                              : "rgba(16, 185, 129, 0.08)",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                          <strong>{risk.risk_type}</strong>
                          <span style={{ fontSize: "0.8rem", fontWeight: "700" }}>{risk.severity}</span>
                        </div>
                        <p style={{ fontSize: "0.88rem", color: "var(--color-text-muted)", margin: "4px 0" }}>{risk.explanation}</p>
                        {risk.flagged_text && (
                          <div style={{ fontStyle: "italic", fontSize: "0.82rem", background: "rgba(0, 0, 0, 0.2)", padding: "8px", borderRadius: "6px", marginTop: "8px" }}>
                            "{risk.flagged_text}"
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <p style={{ color: "var(--color-text-muted)" }}>No high or moderate exposure risks detected.</p>
                  )}
                </div>
              )}

              {activeTab === "clauses" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <h4 style={{ fontSize: "1.1rem", fontWeight: "600" }}>Extracted Clauses</h4>
                  {analysis.result_json.clauses && analysis.result_json.clauses.length > 0 ? (
                    analysis.result_json.clauses.map((clause, i) => (
                      <div key={i} style={{ padding: "12px 16px", borderRadius: "8px", background: "rgba(255, 255, 255, 0.02)", border: "1px solid var(--color-border)" }}>
                        <strong style={{ fontSize: "0.9rem", color: "var(--color-primary)" }}>{clause.clause_type.toUpperCase()}</strong>
                        <p style={{ fontSize: "0.85rem", marginTop: "6px", color: "var(--color-text-muted)" }}>{clause.text}</p>
                      </div>
                    ))
                  ) : (
                    <p style={{ color: "var(--color-text-muted)" }}>No clauses extracted.</p>
                  )}
                </div>
              )}

              {activeTab === "compliance" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <h4 style={{ fontSize: "1.1rem", fontWeight: "600" }}>Statutory Compliance Checks</h4>
                  {analysis.result_json.compliance_issues && analysis.result_json.compliance_issues.length > 0 ? (
                    analysis.result_json.compliance_issues.map((issue, i) => (
                      <div key={i} style={{ padding: "14px", borderRadius: "8px", background: "rgba(255, 255, 255, 0.02)", border: "1px solid var(--color-border)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                          <strong>{issue.statute}</strong>
                          <span style={{ fontSize: "0.78rem" }}>{issue.severity}</span>
                        </div>
                        <p style={{ fontSize: "0.85rem", marginTop: "4px" }}>{issue.issue}</p>
                        <p style={{ fontSize: "0.82rem", color: "var(--color-success)", marginTop: "4px" }}>💡 {issue.recommendation}</p>
                      </div>
                    ))
                  ) : (
                    <p style={{ color: "var(--color-text-muted)" }}>Document complies with applicable statutory standards.</p>
                  )}
                </div>
              )}

              {activeTab === "negotiation" && (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  <h4 style={{ fontSize: "1.1rem", fontWeight: "600" }}>Suggested Redlines & Negotiation Tips</h4>
                  {analysis.result_json.risks && analysis.result_json.risks.filter((r) => r.suggested_revision).length > 0 ? (
                    analysis.result_json.risks
                      .filter((r) => r.suggested_revision)
                      .map((r, i) => (
                        <div key={i} style={{ padding: "14px", borderRadius: "8px", background: "rgba(255, 255, 255, 0.02)", border: "1px solid var(--color-border)" }}>
                          <strong style={{ fontSize: "0.9rem", color: "var(--color-warning)" }}>{r.risk_type}</strong>
                          <div style={{ marginTop: "8px", fontSize: "0.85rem" }}>
                            <div style={{ color: "var(--color-success)", fontWeight: "600", marginBottom: "4px" }}>Suggested Redline:</div>
                            <div style={{ padding: "8px", background: "rgba(16, 185, 129, 0.06)", borderRadius: "6px" }}>{r.suggested_revision}</div>
                          </div>
                          {r.negotiation_tip && (
                            <div style={{ marginTop: "8px", fontSize: "0.82rem", color: "var(--color-text-muted)" }}>
                              <strong>Negotiation Tip:</strong> {r.negotiation_tip}
                            </div>
                          )}
                        </div>
                      ))
                  ) : (
                    <p style={{ color: "var(--color-text-muted)" }}>No redline suggestions generated.</p>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "40px 20px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: "rgba(92, 98, 236, 0.1)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px auto", color: "var(--color-primary)" }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </div>
              <h4 style={{ fontSize: "1.1rem", fontWeight: "600", marginBottom: "8px" }}>No Analysis Recorded Yet</h4>
              <p style={{ fontSize: "0.88rem", color: "var(--color-text-muted)", marginBottom: "20px" }}>
                Click the "Run AI Legal Analysis" button above to initiate the 5-agent LangGraph workflow.
              </p>
              <button className="btn btn-primary btn-sm" onClick={handleRunAnalysis} disabled={isAnalyzing}>
                Start Analysis Now
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
