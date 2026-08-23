import React, { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "../services/api";
import "./ContractDetailPage.css";

interface ContractInfo {
  id: number;
  filename: string;
  upload_path: string;
  status: "pending" | "ingested" | "analyzed" | "failed";
  created_at: string;
}

interface AnalysisPayload {
  contract_id: number;
  status: string;
  document_type?: string;
  metadata?: {
    party_a?: string;
    party_b?: string;
    effective_date?: string;
    jurisdiction?: string;
  };
  clauses?: Record<string, string>;
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
  summary?: string;
}

export const ContractDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [contract, setContract] = useState<ContractInfo | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalysisPayload | null>(null);
  const [rawText, setRawText] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState<"text" | "clauses" | "risks" | "compliance" | "negotiation">("clauses");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [textSearch, setTextSearch] = useState("");
  const [expandedClauses, setExpandedClauses] = useState<Record<string, boolean>>({});
  const [copySuccess, setCopySuccess] = useState(false);

  const fetchWorkspaceData = async () => {
    if (!id) return;
    setIsLoading(true);
    setErrorMsg(null);

    try {
      // 1. Fetch Contract Metadata
      const contractRes = await api.get<ContractInfo>(`/contracts/${id}`);
      setContract(contractRes.data);

      // 2. Fetch Raw Text & Analysis in parallel
      try {
        const textRes = await api.get<{ text: string }>(`/contracts/${id}/text`);
        if (textRes.data?.text) {
          setRawText(textRes.data.text);
        }
      } catch {
        // Raw text not extracted yet, handled gracefully
      }

      try {
        const analysisRes = await api.get<AnalysisPayload>(`/contracts/${id}/analysis`);
        if (analysisRes.data) {
          setAnalysisData(analysisRes.data);
        }
      } catch {
        setAnalysisData(null);
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Failed to load contract intelligence workspace.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkspaceData();
  }, [id]);

  const handleRunAnalysis = async (force: boolean = false) => {
    if (!id) return;
    setIsAnalyzing(true);
    setErrorMsg(null);

    try {
      const response = await api.post<AnalysisPayload>(`/contracts/${id}/analyze?force=${force}`);
      setAnalysisData(response.data);

      // Update contract status in local state
      if (contract) {
        setContract({ ...contract, status: "analyzed" });
      }

      // Re-fetch raw text if needed
      try {
        const textRes = await api.get<{ text: string }>(`/contracts/${id}/text`);
        if (textRes.data?.text) {
          setRawText(textRes.data.text);
        }
      } catch {
        // Ignore text fetch error
      }
    } catch (err: any) {
      const rawDetail = err.response?.data?.detail || err.message || "Multi-Agent Analysis failed.";
      if (typeof rawDetail === "string" && (rawDetail.includes("429") || rawDetail.toLowerCase().includes("quota"))) {
        setErrorMsg("Google AI rate limit reached. Please wait a few seconds while fallback models initialize, then click Re-Run.");
      } else {
        setErrorMsg(typeof rawDetail === "string" ? rawDetail.slice(0, 200) : "Multi-Agent Analysis failed. Please try again.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getDocTypeBadge = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (ext === "pdf") return "PDF";
    if (ext === "docx" || ext === "doc") return "DOCX";
    if (["png", "jpg", "jpeg", "webp"].includes(ext || "")) return "SCAN";
    return "TXT";
  };

  const toggleClause = (clauseKey: string) => {
    setExpandedClauses((prev) => ({
      ...prev,
      [clauseKey]: !prev[clauseKey],
    }));
  };

  const toggleAllClauses = (expand: boolean) => {
    if (!analysisData?.clauses) return;
    const nextState: Record<string, boolean> = {};
    Object.keys(analysisData.clauses).forEach((k) => {
      nextState[k] = expand;
    });
    setExpandedClauses(nextState);
  };

  const handleCopyText = () => {
    if (!rawText) return;
    navigator.clipboard.writeText(rawText);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };

  // Filtered raw text
  const highlightedText = useMemo(() => {
    if (!rawText) return "No text has been extracted from this document yet. Run analysis to extract full text.";
    return rawText;
  }, [rawText]);

  // Clause entries list
  const clauseEntries = useMemo(() => {
    if (!analysisData?.clauses) return [];
    return Object.entries(analysisData.clauses);
  }, [analysisData]);

  // Risk count breakdown
  const riskCounts = useMemo(() => {
    if (!analysisData?.risks) return { red: 0, yellow: 0, green: 0 };
    return {
      red: analysisData.risks.filter((r) => r.severity === "RED_FLAG" || r.severity === "HIGH").length,
      yellow: analysisData.risks.filter((r) => r.severity === "YELLOW_FLAG" || r.severity === "MEDIUM").length,
      green: analysisData.risks.filter((r) => r.severity === "GREEN_FLAG" || r.severity === "LOW").length,
    };
  }, [analysisData]);

  if (isLoading) {
    return (
      <div className="page-loader" style={{ minHeight: "65vh" }}>
        <div className="spinner" />
        <p className="loader-text">Loading Multi-Agent Contract Workspace...</p>
      </div>
    );
  }

  if (!contract) {
    return (
      <div className="placeholder-hero-card" style={{ maxWidth: "600px", margin: "40px auto", textAlign: "center" }}>
        <h2>Contract Not Found</h2>
        <p>The requested document could not be found or you do not have permission to view it.</p>
        <button className="btn btn-primary" onClick={() => navigate("/dashboard")}>
          Return to Contract Vault
        </button>
      </div>
    );
  }

  return (
    <div className="contract-workspace-container">
      {/* Breadcrumbs & Top Quick Actions */}
      <section className="workspace-top-bar">
        <nav className="workspace-breadcrumbs">
          <Link to="/dashboard">Contract Vault</Link>
          <span className="crumb-separator">/</span>
          <span className="crumb-current" title={contract.filename}>
            {contract.filename}
          </span>
        </nav>

        <div className="workspace-header-actions">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate(`/contracts/${contract.id}/ask`)}
            title="Ask grounded questions with citations"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>Ask Grounded Q&A</span>
          </button>

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate(`/contracts/compare?docA=${contract.id}`)}
            title="Compare with another contract version"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M16 3h5v5" />
              <path d="M8 3H3v5" />
              <path d="M12 21V9" />
            </svg>
            <span>Compare</span>
          </button>
        </div>
      </section>

      {errorMsg && (
        <div className="alert alert-danger">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Two-Panel Layout */}
      <div className="workspace-two-panel-grid">
        {/* Left Panel: Executive Overview & Trigger */}
        <div className="workspace-left-panel">
          <div className="contract-meta-card">
            <div className="contract-meta-header">
              <div className="contract-format-avatar">
                {getDocTypeBadge(contract.filename)}
              </div>
              <div className="contract-title-wrapper">
                <h1 title={contract.filename}>{contract.filename}</h1>
                <div className="contract-meta-sub">
                  Ingested on {new Date(contract.created_at).toLocaleDateString()} • ID #{contract.id}
                </div>
              </div>
            </div>

            {/* Analysis Trigger Banner */}
            <div className="analysis-trigger-banner">
              <div className="analysis-trigger-header">
                <div className="analysis-trigger-title">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                  <span>AI Legal Analysis</span>
                </div>
                <span className={`trigger-status-badge ${contract.status}`}>
                  {contract.status === "analyzed" ? "✓ Analyzed" : contract.status}
                </span>
              </div>

              <p style={{ fontSize: "0.82rem", color: "var(--color-text-muted)", margin: 0 }}>
                Comprehensive AI review analyzing legal clauses, key risks, statutory compliance, and contractual obligations.
              </p>

              <button
                className="btn btn-primary"
                onClick={() => handleRunAnalysis(!!analysisData)}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? (
                  <>
                    <div className="spinner spinner-sm" />
                    <span>Analyzing Legal Document...</span>
                  </>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polygon points="5 3 19 12 5 21 5 3" />
                    </svg>
                    <span>{analysisData ? "Re-Run Complete Analysis" : "Run AI Legal Analysis"}</span>
                  </>
                )}
              </button>
            </div>

            {/* Discovered Metadata Key-Values */}
            <div className="meta-kv-grid">
              <div className="meta-kv-item">
                <span className="meta-kv-label">Classification</span>
                <span className="meta-kv-value">
                  {analysisData?.document_type || "Legal Contract"}
                </span>
              </div>
              <div className="meta-kv-item">
                <span className="meta-kv-label">Party A</span>
                <span className="meta-kv-value">
                  {analysisData?.metadata?.party_a || "Extracting..."}
                </span>
              </div>
              <div className="meta-kv-item">
                <span className="meta-kv-label">Party B</span>
                <span className="meta-kv-value">
                  {analysisData?.metadata?.party_b || "Extracting..."}
                </span>
              </div>
              <div className="meta-kv-item">
                <span className="meta-kv-label">Effective Date</span>
                <span className="meta-kv-value">
                  {analysisData?.metadata?.effective_date || "Extracting..."}
                </span>
              </div>
              <div className="meta-kv-item">
                <span className="meta-kv-label">Jurisdiction</span>
                <span className="meta-kv-value">
                  {analysisData?.metadata?.jurisdiction || "Extracting..."}
                </span>
              </div>
            </div>

            {/* Executive AI Legal Summary */}
            <div className="executive-summary-box">
              <div className="executive-summary-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span>Executive Synthesis</span>
              </div>
              <p style={{ margin: 0 }}>
                {analysisData?.summary ||
                  "Run the multi-agent analysis to generate an authoritative executive summary with key liabilities, financial terms, and core obligations."}
              </p>
            </div>
          </div>
        </div>

        {/* Right Panel: Tabbed Inspector */}
        <div className="workspace-right-panel">
          {/* Tab Navigation */}
          <div className="workspace-tab-bar">
            <button
              className={`workspace-tab-btn ${activeTab === "clauses" ? "active" : ""}`}
              onClick={() => setActiveTab("clauses")}
            >
              <span>Key Clauses</span>
              <span className="tab-badge-pill">{clauseEntries.length}</span>
            </button>

            <button
              className={`workspace-tab-btn ${activeTab === "risks" ? "active" : ""}`}
              onClick={() => setActiveTab("risks")}
            >
              <span>Risk Dialectic</span>
              {analysisData?.risks && (
                <span className="tab-badge-pill" style={{ background: "rgba(244, 63, 94, 0.2)", color: "#f43f5e" }}>
                  {riskCounts.red} Red
                </span>
              )}
            </button>

            <button
              className={`workspace-tab-btn ${activeTab === "compliance" ? "active" : ""}`}
              onClick={() => setActiveTab("compliance")}
            >
              <span>Compliance</span>
              <span className="tab-badge-pill">{analysisData?.compliance_issues?.length || 0}</span>
            </button>

            <button
              className={`workspace-tab-btn ${activeTab === "negotiation" ? "active" : ""}`}
              onClick={() => setActiveTab("negotiation")}
            >
              <span>Redlines</span>
            </button>

            <button
              className={`workspace-tab-btn ${activeTab === "text" ? "active" : ""}`}
              onClick={() => setActiveTab("text")}
            >
              <span>Document Text</span>
            </button>
          </div>

          {/* Tab Body */}
          <div className="workspace-tab-body">
            {/* 1. Key Clauses Explorer */}
            {activeTab === "clauses" && (
              <div className="clauses-container">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                  <div style={{ fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
                    Extracted {clauseEntries.length} core legal clauses using RAG taxonomy
                  </div>
                  {clauseEntries.length > 0 && (
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button className="btn btn-secondary btn-xs" onClick={() => toggleAllClauses(true)}>
                        Expand All
                      </button>
                      <button className="btn btn-secondary btn-xs" onClick={() => toggleAllClauses(false)}>
                        Collapse
                      </button>
                    </div>
                  )}
                </div>

                {clauseEntries.length > 0 ? (
                  clauseEntries.map(([key, val]: [string, any]) => {
                    const isExpanded = expandedClauses[key] ?? true;
                    const clauseText =
                      typeof val === "object" && val !== null
                        ? String(val.text || "Not mentioned")
                        : String(val || "Not mentioned");
                    const clauseLocation =
                      typeof val === "object" && val !== null ? val.location : null;

                    return (
                      <div key={key} className="clause-card">
                        <div className="clause-card-header" onClick={() => toggleClause(key)}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span className="clause-type-name">{key.replace(/_/g, " ")}</span>
                            {clauseLocation && clauseLocation !== "Not mentioned" && (
                              <span
                                style={{
                                  fontSize: "0.7rem",
                                  padding: "2px 8px",
                                  borderRadius: "4px",
                                  background: "rgba(255, 255, 255, 0.06)",
                                  color: "var(--color-text-muted)",
                                }}
                              >
                                {clauseLocation}
                              </span>
                            )}
                          </div>
                          <span style={{ fontSize: "0.8rem", color: "var(--color-text-muted)" }}>
                            {isExpanded ? "▲ Hide" : "▼ View"}
                          </span>
                        </div>
                        {isExpanded && (
                          <div className="clause-card-body">
                            {clauseText}
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div style={{ textAlign: "center", padding: "48px 16px", color: "var(--color-text-muted)" }}>
                    <p>No clauses extracted yet. Run the Multi-Agent Analysis to extract legal clauses.</p>
                    <button className="btn btn-primary btn-sm" onClick={() => handleRunAnalysis(false)} disabled={isAnalyzing}>
                      Run Analysis
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* 2. Risk Dialectic Tab */}
            {activeTab === "risks" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                {analysisData?.risks && analysisData.risks.length > 0 ? (
                  analysisData.risks.map((risk, idx) => {
                    const isRed = risk.severity === "RED_FLAG" || risk.severity === "HIGH";
                    const isYellow = risk.severity === "YELLOW_FLAG" || risk.severity === "MEDIUM";
                    return (
                      <div
                        key={idx}
                        style={{
                          padding: "18px",
                          borderRadius: "12px",
                          border: isRed
                            ? "1px solid rgba(244, 63, 94, 0.4)"
                            : isYellow
                            ? "1px solid rgba(245, 158, 11, 0.4)"
                            : "1px solid rgba(16, 185, 129, 0.4)",
                          background: isRed
                            ? "rgba(244, 63, 94, 0.05)"
                            : isYellow
                            ? "rgba(245, 158, 11, 0.05)"
                            : "rgba(16, 185, 129, 0.05)",
                          display: "flex",
                          flexDirection: "column",
                          gap: "8px",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <strong style={{ fontSize: "0.95rem" }}>{risk.risk_type}</strong>
                          <span
                            style={{
                              fontSize: "0.74rem",
                              fontWeight: "700",
                              padding: "3px 8px",
                              borderRadius: "6px",
                              background: isRed ? "var(--color-danger)" : isYellow ? "var(--color-warning)" : "var(--color-success)",
                              color: "#fff",
                            }}
                          >
                            {risk.severity}
                          </span>
                        </div>
                        <p style={{ fontSize: "0.88rem", color: "var(--color-text-main)", margin: "4px 0" }}>
                          {risk.explanation}
                        </p>
                        {(risk as any).flagged_text || (risk as any).clause_text ? (
                          <div
                            style={{
                              fontSize: "0.82rem",
                              fontStyle: "italic",
                              padding: "8px 12px",
                              background: "rgba(0, 0, 0, 0.25)",
                              borderRadius: "6px",
                              borderLeft: "3px solid var(--color-border)",
                            }}
                          >
                            "{(risk as any).flagged_text || (risk as any).clause_text}"
                          </div>
                        ) : null}
                      </div>
                    );
                  })
                ) : (
                  <p style={{ color: "var(--color-text-muted)", textAlign: "center", padding: "40px 0" }}>
                    No risks assessed yet. Run the Multi-Agent Analysis to trigger the 3-Tier Risk Dialectic.
                  </p>
                )}
              </div>
            )}

            {/* 3. Compliance Tab */}
            {activeTab === "compliance" && (
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {analysisData?.compliance_issues && analysisData.compliance_issues.length > 0 ? (
                  analysisData.compliance_issues.map((item: any, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "16px",
                        borderRadius: "10px",
                        border: "1px solid var(--color-border)",
                        background: "var(--color-surface-elevated)",
                        display: "flex",
                        flexDirection: "column",
                        gap: "6px",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <strong style={{ color: "var(--color-primary)", fontSize: "0.9rem" }}>
                          {item.statute || item.issue_type || item.clause_type || "Compliance Standard"}
                        </strong>
                        <span style={{ fontSize: "0.75rem", fontWeight: "600" }}>{item.severity}</span>
                      </div>
                      <p style={{ fontSize: "0.86rem", margin: 0 }}>{item.issue || item.explanation}</p>
                      <div style={{ fontSize: "0.82rem", color: "var(--color-success)", marginTop: "4px" }}>
                        💡 <strong>Recommendation:</strong> {item.recommendation}
                      </div>
                    </div>
                  ))
                ) : (
                  <p style={{ color: "var(--color-text-muted)", textAlign: "center", padding: "40px 0" }}>
                    Document benchmarked against statutory codes. Run analysis to check compliance.
                  </p>
                )}
              </div>
            )}

            {/* 4. Strategic Redlines Tab */}
            {activeTab === "negotiation" && (
              <div className="redlines-container">
                {analysisData?.risks && analysisData.risks.filter((r) => r.suggested_revision).length > 0 ? (
                  analysisData.risks
                    .filter((r) => r.suggested_revision)
                    .map((r, idx) => (
                      <div key={idx} className="redline-card">
                        <span className="redline-clause-tag">{r.risk_type}</span>
                        <div className="redline-box">
                          <div style={{ fontSize: "0.76rem", fontWeight: "700", color: "var(--color-success)", marginBottom: "4px" }}>
                            SUGGESTED REDLINE CLAUSE:
                          </div>
                          {r.suggested_revision}
                        </div>
                        {r.negotiation_tip && (
                          <div className="negotiation-tip-box">
                            <strong>Negotiation Strategy:</strong> {r.negotiation_tip}
                          </div>
                        )}
                      </div>
                    ))
                ) : (
                  <p style={{ color: "var(--color-text-muted)", textAlign: "center", padding: "40px 0" }}>
                    No redline revisions available. Run analysis to generate negotiation suggestions.
                  </p>
                )}
              </div>
            )}

            {/* 5. Document Text Tab */}
            {activeTab === "text" && (
              <div>
                <div className="doc-text-toolbar">
                  <div className="doc-text-search-box">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                      type="text"
                      placeholder="Search document text..."
                      value={textSearch}
                      onChange={(e) => setTextSearch(e.target.value)}
                    />
                  </div>

                  <button className="btn btn-secondary btn-xs" onClick={handleCopyText}>
                    {copySuccess ? "✓ Copied!" : "Copy Full Text"}
                  </button>
                </div>

                <div className="raw-text-viewer-box">
                  {highlightedText}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
