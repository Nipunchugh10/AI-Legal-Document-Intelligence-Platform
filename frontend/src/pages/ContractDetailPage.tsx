import React, { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "../services/api";
import "./ContractDetailPage.css";

interface ContractInfo {
  id: number;
  filename: string;
  upload_path: string;
  status: "pending" | "ingested" | "processing" | "analyzed" | "failed";
  created_at: string;
}

interface RiskItem {
  risk_type: string;
  flag_category?: "RED_FLAG" | "YELLOW_FLAG" | "GREEN_FLAG";
  severity: "RED_FLAG" | "YELLOW_FLAG" | "GREEN_FLAG" | "HIGH" | "MEDIUM" | "LOW";
  explanation: string;
  clause_text?: string;
  flagged_text?: string;
  suggestion?: string;
  suggested_revision?: string;
  negotiation_tip?: string;
  irac_issue?: string;
  irac_rule?: string;
  irac_analysis?: string;
  irac_conclusion?: string;
}

interface ComplianceItem {
  statute?: string;
  domain?: string;
  issue_type?: string;
  clause_type?: string;
  issue?: string;
  explanation?: string;
  severity: "HIGH" | "MEDIUM" | "LOW" | "VIOLATION" | "DEVIATION" | "COMPLIANT";
  recommendation: string;
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
    governing_law?: string;
    financial_terms?: string;
    liability_cap_status?: string;
    termination_notice?: string;
  };
  clauses?: Record<string, string | { text: string; location?: string; present?: boolean }>;
  risks?: RiskItem[];
  compliance_issues?: ComplianceItem[];
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
  const [activeTab, setActiveTab] = useState<"overview" | "clauses" | "risks" | "compliance" | "negotiation" | "text">("overview");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters & State
  const [riskFilter, setRiskFilter] = useState<"ALL" | "RED" | "YELLOW" | "GREEN">("ALL");
  const [riskSearch, setRiskSearch] = useState("");
  const [complianceDomainFilter, setComplianceDomainFilter] = useState<string>("ALL");
  const [complianceSearch, setComplianceSearch] = useState("");
  const [clauseSearch, setClauseSearch] = useState("");
  const [textSearch, setTextSearch] = useState("");
  const [expandedClauses, setExpandedClauses] = useState<Record<string, boolean>>({});
  const [selectedRedlineTier, setSelectedRedlineTier] = useState<Record<number, "balanced" | "protective" | "aggressive">>({});
  const [copyStatus, setCopyStatus] = useState<string | null>(null);

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

  // Polling hook when contract is processing in background
  useEffect(() => {
    let interval: ReturnType<typeof setInterval> | null = null;

    if (contract?.status === "processing" || isAnalyzing) {
      interval = setInterval(async () => {
        try {
          const res = await api.get<ContractInfo>(`/contracts/${id}`);
          if (res.data.status === "analyzed") {
            setContract(res.data);
            setIsAnalyzing(false);
            // Fetch completed analysis payload & raw text
            const [analysisRes, textRes] = await Promise.allSettled([
              api.get<AnalysisPayload>(`/contracts/${id}/analysis`),
              api.get<{ text: string }>(`/contracts/${id}/text`),
            ]);
            if (analysisRes.status === "fulfilled" && analysisRes.value.data) {
              setAnalysisData(analysisRes.value.data);
            }
            if (textRes.status === "fulfilled" && textRes.value.data?.text) {
              setRawText(textRes.value.data.text);
            }
          } else if (res.data.status === "failed") {
            setContract(res.data);
            setIsAnalyzing(false);
            setErrorMsg("Background contract analysis encountered an issue. Please click 'Re-Run Multi-Agent Analysis'.");
          }
        } catch {
          // Ignore transient polling failure
        }
      }, 2500);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [contract?.status, isAnalyzing, id]);

  const handleRunAnalysis = async (force: boolean = false) => {
    if (!id) return;
    setIsAnalyzing(true);
    setErrorMsg(null);

    try {
      const response = await api.post<AnalysisPayload>(`/contracts/${id}/analyze?force=${force}`);
      if (response.data.status === "analyzed") {
        setAnalysisData(response.data);
        if (contract) {
          setContract({ ...contract, status: "analyzed" });
        }
        setIsAnalyzing(false);
      } else {
        // Status is processing in background
        if (contract) {
          setContract({ ...contract, status: "processing" });
        }
      }

      try {
        const textRes = await api.get<{ text: string }>(`/contracts/${id}/text`);
        if (textRes.data?.text) {
          setRawText(textRes.data.text);
        }
      } catch {
        // Ignore text fetch error
      }
    } catch (err: any) {
      setIsAnalyzing(false);
      const rawDetail = err.response?.data?.detail || err.message || "Multi-Agent Analysis failed.";
      if (typeof rawDetail === "string" && (rawDetail.includes("429") || rawDetail.toLowerCase().includes("quota"))) {
        setErrorMsg("Google AI rate limit reached. Please wait a few seconds while fallback models initialize, then click Re-Run.");
      } else {
        setErrorMsg(typeof rawDetail === "string" ? rawDetail.slice(0, 200) : "Multi-Agent Analysis failed. Please try again.");
      }
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

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopyStatus(label);
    setTimeout(() => setCopyStatus(null), 2000);
  };

  // Clause entries list
  const clauseEntries = useMemo(() => {
    if (!analysisData?.clauses) return [];
    return Object.entries(analysisData.clauses).filter(([key, val]) => {
      if (!clauseSearch.trim()) return true;
      const text = typeof val === "object" && val !== null ? String(val.text || "") : String(val || "");
      return key.toLowerCase().includes(clauseSearch.toLowerCase()) || text.toLowerCase().includes(clauseSearch.toLowerCase());
    });
  }, [analysisData, clauseSearch]);

  // Risk count breakdown
  const riskCounts = useMemo(() => {
    if (!analysisData?.risks) return { red: 0, yellow: 0, green: 0, total: 0 };
    const red = analysisData.risks.filter((r) => r.flag_category === "RED_FLAG" || r.severity === "RED_FLAG" || r.severity === "HIGH").length;
    const yellow = analysisData.risks.filter((r) => r.flag_category === "YELLOW_FLAG" || r.severity === "YELLOW_FLAG" || r.severity === "MEDIUM").length;
    const green = analysisData.risks.filter((r) => r.flag_category === "GREEN_FLAG" || r.severity === "GREEN_FLAG" || r.severity === "LOW").length;
    return { red, yellow, green, total: analysisData.risks.length };
  }, [analysisData]);

  // Dynamic Contract Risk Score Computation (0 - 100)
  const riskScoreData = useMemo(() => {
    if (!analysisData?.risks || analysisData.risks.length === 0) {
      return { score: 0, label: "Not Analyzed", tier: "neutral", color: "#94a3b8" };
    }

    // Weighted risk computation: Red = 25, Yellow = 10, Green = -5
    const computed = riskCounts.red * 25 + riskCounts.yellow * 10 - riskCounts.green * 5;
    const boundedScore = Math.min(100, Math.max(5, computed));

    if (boundedScore >= 75 || riskCounts.red >= 3) {
      return { score: boundedScore, label: "Critical Exposure — High Risk", tier: "danger", color: "#f43f5e" };
    }
    if (boundedScore >= 45 || riskCounts.red >= 1) {
      return { score: boundedScore, label: "Elevated Concern — Lawyer Review Advised", tier: "warning", color: "#f59e0b" };
    }
    if (boundedScore >= 20 || riskCounts.yellow >= 1) {
      return { score: boundedScore, label: "Moderate Risk — Standard Commercial Terms", tier: "moderate", color: "#38bdf8" };
    }
    return { score: boundedScore, label: "Protective & Favorable Terms", tier: "success", color: "#10b981" };
  }, [analysisData, riskCounts]);

  // Filtered Risks List
  const filteredRisks = useMemo(() => {
    if (!analysisData?.risks) return [];
    return analysisData.risks.filter((r) => {
      const isRed = r.flag_category === "RED_FLAG" || r.severity === "RED_FLAG" || r.severity === "HIGH";
      const isYellow = r.flag_category === "YELLOW_FLAG" || r.severity === "YELLOW_FLAG" || r.severity === "MEDIUM";
      const isGreen = r.flag_category === "GREEN_FLAG" || r.severity === "GREEN_FLAG" || r.severity === "LOW";

      if (riskFilter === "RED" && !isRed) return false;
      if (riskFilter === "YELLOW" && !isYellow) return false;
      if (riskFilter === "GREEN" && !isGreen) return false;

      if (riskSearch.trim()) {
        const q = riskSearch.toLowerCase();
        const text = (r.clause_text || r.flagged_text || "").toLowerCase();
        const exp = (r.explanation || "").toLowerCase();
        const type = (r.risk_type || "").toLowerCase();
        return text.includes(q) || exp.includes(q) || type.includes(q);
      }
      return true;
    });
  }, [analysisData, riskFilter, riskSearch]);

  // 8 Statutory Domains mapping & filtering
  const complianceDomains = [
    { id: "ALL", name: "All Domains" },
    { id: "property", name: "Property & Real Estate" },
    { id: "corporate", name: "Corporate & Business" },
    { id: "labour", name: "Labour & Employment" },
    { id: "disputes", name: "Courts & Litigation" },
    { id: "banking", name: "Banking & Finance" },
    { id: "ip", name: "IP & Technology" },
    { id: "posh", name: "Human Rights & POSH" },
    { id: "trade", name: "International Trade" },
    { id: "dpdp", name: "DPDP Act 2023 (Privacy)" },
  ];

  const filteredCompliance = useMemo(() => {
    if (!analysisData?.compliance_issues) return [];
    return analysisData.compliance_issues.filter((item) => {
      if (complianceDomainFilter !== "ALL") {
        const target = complianceDomainFilter.toLowerCase();
        const text = `${item.statute || ""} ${item.domain || ""} ${item.issue_type || ""} ${item.clause_type || ""}`.toLowerCase();
        if (!text.includes(target)) return false;
      }
      if (complianceSearch.trim()) {
        const q = complianceSearch.toLowerCase();
        const content = `${item.statute || ""} ${item.issue || item.explanation || ""} ${item.recommendation || ""}`.toLowerCase();
        return content.includes(q);
      }
      return true;
    });
  }, [analysisData, complianceDomainFilter, complianceSearch]);

  // Multi-tier Redline generation helper
  const getRedlineDrafts = (risk: RiskItem) => {
    const baseSuggestion = risk.suggested_revision || risk.suggestion || "Notwithstanding any provision to the contrary, liability shall be capped at the total fees paid under this Agreement.";
    const originalClause = risk.clause_text || risk.flagged_text || "Original clause not specified in document text";

    return {
      original: originalClause,
      balanced: baseSuggestion,
      protective: `Subject to applicable statutory requirements, the total aggregate liability of either party for all claims arising out of or related to this Agreement shall be strictly limited to the direct damages incurred, not to exceed the total fees actually paid in the twelve (12) months preceding the event. Neither party shall be liable for indirect, incidental, punitive, or consequential damages.`,
      aggressive: `The Receiving/Contracting Party shall have zero financial liability whatsoever for any direct or indirect damages, losses, or claims arising out of this Agreement. The Disclosing/Client Party agrees to fully indemnify, defend, and hold harmless the Contracting Party against any third-party claims, legal fees, or liabilities without limitation.`,
    };
  };

  // Export Full Legal Audit Report
  const handleExportReport = () => {
    if (!contract || !analysisData) return;

    const markdownContent = `# Legal Intelligence & Risk Audit Report
**Document:** ${contract.filename}
**Analysis Date:** ${new Date().toLocaleDateString()}
**Document Type:** ${analysisData.document_type || "Commercial Legal Contract"}
**Risk Score:** ${riskScoreData.score}/100 (${riskScoreData.label})

---

## 1. Executive Summary
${analysisData.summary || "No executive summary available."}

---

## 2. Key Contract Metadata
- **Party A:** ${analysisData.metadata?.party_a || "Not specified"}
- **Party B:** ${analysisData.metadata?.party_b || "Not specified"}
- **Effective Date:** ${analysisData.metadata?.effective_date || "Not specified"}
- **Governing Jurisdiction:** ${analysisData.metadata?.jurisdiction || "Not specified"}

---

## 3. 3-Tier Traffic Light Risk Dialectic (${riskCounts.total} Identified Flags)
${(analysisData.risks || [])
  .map(
    (r, idx) => `### ${idx + 1}. [${r.flag_category || r.severity}] ${r.risk_type}
- **Explanation:** ${r.explanation}
- **Flagged Clause:** "${r.clause_text || r.flagged_text || "N/A"}"
- **Suggested Revision:** ${r.suggested_revision || r.suggestion || "Review with lawyer"}
- **Negotiation Strategy:** ${r.negotiation_tip || "Align with market fair standards"}
`
  )
  .join("\n")}

---

## 4. 8-Domain Statutory Compliance Audit
${(analysisData.compliance_issues || [])
  .map(
    (c, idx) => `### ${idx + 1}. ${c.statute || c.issue_type || "Compliance Standard"} [${c.severity}]
- **Issue:** ${c.issue || c.explanation || "N/A"}
- **Recommendation:** ${c.recommendation}
`
  )
  .join("\n")}

---
*Generated by AI Legal Document Intelligence Platform (Google Antigravity & Gemini LLM)*
`;

    const blob = new Blob([markdownContent], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Legal_Audit_Report_${contract.filename.replace(/\.[^/.]+$/, "")}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="page-loader" style={{ minHeight: "65vh" }}>
        <div className="spinner" />
        <p className="loader-text">Loading Multi-Agent Legal Workspace...</p>
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
      {/* Top Breadcrumb & Action Bar */}
      <section className="workspace-top-bar">
        <nav className="workspace-breadcrumbs">
          <Link to="/dashboard">Contract Vault</Link>
          <span className="crumb-separator">/</span>
          <span className="crumb-current" title={contract.filename}>
            {contract.filename}
          </span>
        </nav>

        <div className="workspace-header-actions">
          {analysisData && (
            <>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleExportReport}
                title="Download formatted Markdown Legal Audit Report"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                <span>Export Audit Report</span>
              </button>

              <button
                className="btn btn-secondary btn-sm"
                onClick={() => copyToClipboard(analysisData.summary || "", "Executive Report")}
                title="Copy Executive Report to Clipboard"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
                <span>{copyStatus === "Executive Report" ? "✓ Copied!" : "Copy Report"}</span>
              </button>
            </>
          )}

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate(`/contracts/${contract.id}/ask`)}
            title="Ask grounded questions with pinpoint clause citations"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span>Ask Grounded Q&A</span>
          </button>

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => navigate(`/contracts/compare?docA=${contract.id}`)}
            title="Compare with another contract version"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M16 3h5v5" />
              <path d="M8 3H3v5" />
              <path d="M12 21V9" />
            </svg>
            <span>Compare Diff</span>
          </button>
        </div>
      </section>

      {errorMsg && (
        <div className="alert alert-danger" style={{ margin: "0 0 20px 0" }}>
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
        {/* Left Panel: Document Overview & Risk Engine */}
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

            {/* Overall Contract Risk Score Meter */}
            <div className="risk-score-card">
              <div className="risk-score-header">
                <div className="risk-score-title">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                  <span>Overall Risk Score</span>
                </div>
                <div className="risk-score-number" style={{ color: riskScoreData.color }}>
                  {riskScoreData.score}
                  <span className="risk-score-max">/100</span>
                </div>
              </div>

              {/* Score Progress Bar */}
              <div className="risk-meter-bar-track">
                <div
                  className="risk-meter-bar-fill"
                  style={{
                    width: `${riskScoreData.score}%`,
                    background:
                      riskScoreData.tier === "danger"
                        ? "linear-gradient(90deg, #f59e0b, #f43f5e)"
                        : riskScoreData.tier === "warning"
                        ? "linear-gradient(90deg, #38bdf8, #f59e0b)"
                        : riskScoreData.tier === "moderate"
                        ? "linear-gradient(90deg, #10b981, #38bdf8)"
                        : "#10b981",
                  }}
                />
              </div>

              <div className="risk-score-label-badge" style={{ color: riskScoreData.color }}>
                {riskScoreData.label}
              </div>

              {/* Risk Flag Metrics Pills */}
              <div className="risk-summary-pills">
                <div className="risk-pill red">
                  <span className="risk-dot red" />
                  <span>{riskCounts.red} Critical Red</span>
                </div>
                <div className="risk-pill yellow">
                  <span className="risk-dot yellow" />
                  <span>{riskCounts.yellow} Yellow Concerns</span>
                </div>
                <div className="risk-pill green">
                  <span className="risk-dot green" />
                  <span>{riskCounts.green} Protective</span>
                </div>
              </div>
            </div>

            {/* Analysis Trigger Banner */}
            <div className="analysis-trigger-banner">
              <div className="analysis-trigger-header">
                <div className="analysis-trigger-title">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  <span>Multi-Agent Dialectic</span>
                </div>
                <span className={`trigger-status-badge ${contract.status}`}>
                  {contract.status === "analyzed" ? "✓ Analyzed" : contract.status}
                </span>
              </div>

              <p style={{ fontSize: "0.82rem", color: "var(--color-text-muted)", margin: "4px 0 10px 0" }}>
                Simulates Plaintiff & Defense counsel adversarial dialectic with statutory verification across 8 legal domains.
              </p>

              <button
                className="btn btn-primary"
                onClick={() => handleRunAnalysis(!!analysisData)}
                disabled={isAnalyzing}
                style={{ width: "100%" }}
              >
                {isAnalyzing ? (
                  <>
                    <div className="spinner spinner-sm" />
                    <span>Executing Legal Dialectic...</span>
                  </>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polygon points="5 3 19 12 5 21 5 3" />
                    </svg>
                    <span>{analysisData ? "Re-Run Elite Legal Analysis" : "Run AI Legal Analysis"}</span>
                  </>
                )}
              </button>
            </div>

            {/* Discovered Metadata Key-Values */}
            <div className="meta-kv-grid">
              <div className="meta-kv-item">
                <span className="meta-kv-label">Classification</span>
                <span className="meta-kv-value">{analysisData?.document_type || "Legal Contract"}</span>
              </div>
              <div className="meta-kv-item">
                <span className="meta-kv-label">Party A (Disclosing/Client)</span>
                <span className="meta-kv-value">{analysisData?.metadata?.party_a || "Extracting..."}</span>
              </div>
              <div className="meta-kv-item">
                <span className="meta-kv-label">Party B (Receiving/Vendor)</span>
                <span className="meta-kv-value">{analysisData?.metadata?.party_b || "Extracting..."}</span>
              </div>
              <div className="meta-kv-item">
                <span className="meta-kv-label">Effective Date</span>
                <span className="meta-kv-value">{analysisData?.metadata?.effective_date || "Extracting..."}</span>
              </div>
              <div className="meta-kv-item">
                <span className="meta-kv-label">Governing Jurisdiction</span>
                <span className="meta-kv-value">{analysisData?.metadata?.jurisdiction || "Extracting..."}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel: 5-Tab Elite Legal Analysis Inspector */}
        <div className="workspace-right-panel">
          {/* Tab Navigation */}
          <div className="workspace-tab-bar">
            <button
              className={`workspace-tab-btn ${activeTab === "overview" ? "active" : ""}`}
              onClick={() => setActiveTab("overview")}
            >
              <span>Executive Overview</span>
            </button>

            <button
              className={`workspace-tab-btn ${activeTab === "risks" ? "active" : ""}`}
              onClick={() => setActiveTab("risks")}
            >
              <span>3-Tier Risk Dialectic</span>
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
              <span>8-Domain Compliance</span>
              <span className="tab-badge-pill">{analysisData?.compliance_issues?.length || 0}</span>
            </button>

            <button
              className={`workspace-tab-btn ${activeTab === "negotiation" ? "active" : ""}`}
              onClick={() => setActiveTab("negotiation")}
            >
              <span>Redline Counter-Drafts</span>
            </button>

            <button
              className={`workspace-tab-btn ${activeTab === "clauses" ? "active" : ""}`}
              onClick={() => setActiveTab("clauses")}
            >
              <span>Key Clauses</span>
              <span className="tab-badge-pill">{clauseEntries.length}</span>
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
            {/* 1. Executive Overview Tab */}
            {activeTab === "overview" && (
              <div className="tab-overview-container">
                <div className="executive-synthesis-card">
                  <div className="executive-synthesis-header">
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                        <polyline points="10 9 9 9 8 9" />
                      </svg>
                      <strong>Senior Partner Executive Synthesis</strong>
                    </div>
                    <button
                      className="btn btn-secondary btn-xs"
                      onClick={() => copyToClipboard(analysisData?.summary || "", "Summary")}
                    >
                      {copyStatus === "Summary" ? "✓ Copied" : "Copy Synthesis"}
                    </button>
                  </div>
                  <div className="executive-summary-prose">
                    {analysisData?.summary ? (
                      analysisData.summary
                    ) : (contract.status === "processing" || isAnalyzing) ? (
                      <div style={{ padding: "32px 16px", display: "flex", flexDirection: "column", alignItems: "center", gap: "16px", textAlign: "center" }}>
                        <div className="spinner" style={{ width: "36px", height: "36px" }} />
                        <div>
                          <h4 style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--color-text-main)", marginBottom: "4px" }}>
                            Multi-Agent Legal Analysis in Progress...
                          </h4>
                          <p style={{ fontSize: "0.86rem", color: "var(--color-text-muted)", maxWidth: "460px" }}>
                            Our 5-agent LangGraph orchestrator is parsing clauses, assessing 3-tier IRAC risks, and running statutory compliance audits in the background.
                          </p>
                        </div>
                        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", justifyContent: "center", marginTop: "8px" }}>
                          <span className="tab-badge-pill" style={{ background: "rgba(92, 98, 236, 0.15)", color: "var(--color-primary)" }}>1. Document Parser</span>
                          <span className="tab-badge-pill" style={{ background: "rgba(92, 98, 236, 0.15)", color: "var(--color-primary)" }}>2. Clause Extractor</span>
                          <span className="tab-badge-pill" style={{ background: "rgba(92, 98, 236, 0.15)", color: "var(--color-primary)" }}>3. IRAC Risk Agent</span>
                          <span className="tab-badge-pill" style={{ background: "rgba(92, 98, 236, 0.15)", color: "var(--color-primary)" }}>4. Statutory Compliance</span>
                          <span className="tab-badge-pill" style={{ background: "rgba(92, 98, 236, 0.15)", color: "var(--color-primary)" }}>5. Senior Partner Synthesis</span>
                        </div>
                      </div>
                    ) : (
                      <div style={{ textAlign: "center", padding: "30px 10px", color: "var(--color-text-muted)" }}>
                        <p>No analysis generated yet. Click "Run AI Legal Analysis" to trigger multi-agent review.</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Key Legal Obligations Grid */}
                <div className="legal-highlights-grid">
                  <div className="highlight-card">
                    <div className="highlight-label">Financial & Payment Terms</div>
                    <div className="highlight-value">
                      {typeof analysisData?.clauses?.payment_terms === "object" && analysisData.clauses.payment_terms !== null
                        ? analysisData.clauses.payment_terms.text?.slice(0, 140) + "..."
                        : typeof analysisData?.clauses?.payment_terms === "string"
                        ? analysisData.clauses.payment_terms.slice(0, 140) + "..."
                        : "Standard Milestone terms or extracted via Clause tab"}
                    </div>
                  </div>

                  <div className="highlight-card">
                    <div className="highlight-label">Liability & Cap Exposure</div>
                    <div className="highlight-value">
                      {typeof analysisData?.clauses?.liability_clauses === "object" && analysisData.clauses.liability_clauses !== null
                        ? analysisData.clauses.liability_clauses.text?.slice(0, 140) + "..."
                        : typeof analysisData?.clauses?.liability_clauses === "string"
                        ? analysisData.clauses.liability_clauses.slice(0, 140) + "..."
                        : "Extracted via Liability clause analysis"}
                    </div>
                  </div>

                  <div className="highlight-card">
                    <div className="highlight-label">Termination & Exit Conditions</div>
                    <div className="highlight-value">
                      {typeof analysisData?.clauses?.termination_clauses === "object" && analysisData.clauses.termination_clauses !== null
                        ? analysisData.clauses.termination_clauses.text?.slice(0, 140) + "..."
                        : typeof analysisData?.clauses?.termination_clauses === "string"
                        ? analysisData.clauses.termination_clauses.slice(0, 140) + "..."
                        : "Extracted via Termination clause analysis"}
                    </div>
                  </div>

                  <div className="highlight-card">
                    <div className="highlight-label">Dispute & Governing Law</div>
                    <div className="highlight-value">
                      {typeof analysisData?.clauses?.dispute_resolution_clauses === "object" && analysisData.clauses.dispute_resolution_clauses !== null
                        ? analysisData.clauses.dispute_resolution_clauses.text?.slice(0, 140) + "..."
                        : typeof analysisData?.clauses?.dispute_resolution_clauses === "string"
                        ? analysisData.clauses.dispute_resolution_clauses.slice(0, 140) + "..."
                        : "Arbitration & Conciliation Act / Jurisdiction"}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 2. 3-Tier Traffic Light Risk Dialectic Tab */}
            {activeTab === "risks" && (
              <div className="tab-risks-container">
                {/* Risk Filter & Search Toolbar */}
                <div className="risk-toolbar">
                  <div className="risk-filter-pills">
                    <button
                      className={`risk-filter-btn ${riskFilter === "ALL" ? "active" : ""}`}
                      onClick={() => setRiskFilter("ALL")}
                    >
                      All Flags ({riskCounts.total})
                    </button>
                    <button
                      className={`risk-filter-btn red ${riskFilter === "RED" ? "active" : ""}`}
                      onClick={() => setRiskFilter("RED")}
                    >
                      🔴 Critical Red ({riskCounts.red})
                    </button>
                    <button
                      className={`risk-filter-btn yellow ${riskFilter === "YELLOW" ? "active" : ""}`}
                      onClick={() => setRiskFilter("YELLOW")}
                    >
                      🟡 Moderate ({riskCounts.yellow})
                    </button>
                    <button
                      className={`risk-filter-btn green ${riskFilter === "GREEN" ? "active" : ""}`}
                      onClick={() => setRiskFilter("GREEN")}
                    >
                      🟢 Protective ({riskCounts.green})
                    </button>
                  </div>

                  <div className="risk-search-box">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                      type="text"
                      placeholder="Filter risks by keyword..."
                      value={riskSearch}
                      onChange={(e) => setRiskSearch(e.target.value)}
                    />
                  </div>
                </div>

                {/* Risk Cards List with IRAC Breakdown */}
                {filteredRisks.length > 0 ? (
                  filteredRisks.map((risk, idx) => {
                    const isRed = risk.flag_category === "RED_FLAG" || risk.severity === "RED_FLAG" || risk.severity === "HIGH";
                    const isYellow = risk.flag_category === "YELLOW_FLAG" || risk.severity === "YELLOW_FLAG" || risk.severity === "MEDIUM";
                    const cardClass = isRed ? "risk-card red" : isYellow ? "risk-card yellow" : "risk-card green";
                    const badgeText = isRed ? "🔴 RED FLAG (Critical)" : isYellow ? "🟡 YELLOW FLAG (Concern)" : "🟢 GREEN FLAG (Protective)";

                    return (
                      <div key={idx} className={cardClass}>
                        <div className="risk-card-header">
                          <div className="risk-title-wrapper">
                            <strong className="risk-type-title">{risk.risk_type.replace(/_/g, " ")}</strong>
                            <span className="risk-category-badge">{badgeText}</span>
                          </div>
                          {risk.suggested_revision && (
                            <button
                              className="btn btn-secondary btn-xs"
                              onClick={() => setActiveTab("negotiation")}
                              title="Jump to Redlines Tab to view counter-draft"
                            >
                              View Redline ➔
                            </button>
                          )}
                        </div>

                        {/* IRAC Legal Reasoning Grid */}
                        <div className="irac-grid">
                          <div className="irac-item">
                            <span className="irac-tag issue">ISSUE</span>
                            <p className="irac-content">
                              {risk.irac_issue || risk.explanation || "Contractual vulnerability identified in dialectic."}
                            </p>
                          </div>

                          <div className="irac-item">
                            <span className="irac-tag rule">STATUTORY RULE</span>
                            <p className="irac-content">
                              {risk.irac_rule ||
                                (isRed
                                  ? "Indian Contract Act 1872 (Section 27 / 74) & DPDP Act 2023 Statutory Compliance Benchmark"
                                  : "Standard Commercial Law Fair Dealing & Market Equity Standards")}
                            </p>
                          </div>

                          <div className="irac-item">
                            <span className="irac-tag analysis">LEGAL ANALYSIS</span>
                            <p className="irac-content">
                              {risk.irac_analysis ||
                                (isRed
                                  ? "The clause creates uncapped exposure or enforces unilateral obligations that shift fatal commercial liability."
                                  : "Clause contains ambiguous notice or execution timelines that require clarification with opposing counsel.")}
                            </p>
                          </div>

                          <div className="irac-item">
                            <span className="irac-tag conclusion">TACTICAL STRATEGY</span>
                            <p className="irac-content">
                              {risk.negotiation_tip || risk.suggestion || "Seek counter-draft revision before execution."}
                            </p>
                          </div>
                        </div>

                        {/* Flagged Clause Snippet */}
                        {(risk.clause_text || risk.flagged_text) && (
                          <div className="flagged-snippet-box">
                            <div className="snippet-header">
                              <span>VERBATIM CLAUSE TEXT:</span>
                              <button
                                className="btn-copy-snippet"
                                onClick={() => copyToClipboard(risk.clause_text || risk.flagged_text || "", `Clause-${idx}`)}
                              >
                                {copyStatus === `Clause-${idx}` ? "✓ Copied" : "Copy Clause"}
                              </button>
                            </div>
                            <div className="snippet-body">
                              "{risk.clause_text || risk.flagged_text}"
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div style={{ textAlign: "center", padding: "48px 16px", color: "var(--color-text-muted)" }}>
                    <p>No risk flags match the current filters.</p>
                  </div>
                )}
              </div>
            )}

            {/* 3. 8-Domain Statutory Compliance Tab */}
            {activeTab === "compliance" && (
              <div className="tab-compliance-container">
                {/* Domain Selector & Search */}
                <div className="compliance-toolbar">
                  <div className="domain-select-wrapper">
                    <label>Filter by Statutory Domain:</label>
                    <select
                      value={complianceDomainFilter}
                      onChange={(e) => setComplianceDomainFilter(e.target.value)}
                    >
                      {complianceDomains.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="risk-search-box">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                      type="text"
                      placeholder="Search compliance issues..."
                      value={complianceSearch}
                      onChange={(e) => setComplianceSearch(e.target.value)}
                    />
                  </div>
                </div>

                {filteredCompliance.length > 0 ? (
                  <div className="compliance-cards-grid">
                    {filteredCompliance.map((item, idx) => {
                      const isViolation = item.severity === "HIGH" || item.severity === "VIOLATION";
                      const isDeviation = item.severity === "MEDIUM" || item.severity === "DEVIATION";
                      const severityClass = isViolation ? "violation" : isDeviation ? "deviation" : "compliant";
                      const badgeText = isViolation ? "Statutory Violation" : isDeviation ? "Minor Deviation" : "Compliant Standard";

                      return (
                        <div key={idx} className={`compliance-card ${severityClass}`}>
                          <div className="compliance-card-header">
                            <div className="statute-title">
                              <span className="statute-icon">⚖️</span>
                              <strong>{item.statute || item.issue_type || item.clause_type || "Legal Standard"}</strong>
                            </div>
                            <span className={`compliance-status-badge ${severityClass}`}>{badgeText}</span>
                          </div>

                          <div className="compliance-issue-text">
                            <strong>Observed Issue:</strong> {item.issue || item.explanation}
                          </div>

                          <div className="compliance-recommendation-box">
                            <div className="rec-title">💡 Actionable Corrective Amendment:</div>
                            <div className="rec-content">{item.recommendation}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ textAlign: "center", padding: "48px 16px", color: "var(--color-text-muted)" }}>
                    <p>No compliance issues found matching the selected domain.</p>
                  </div>
                )}
              </div>
            )}

            {/* 4. Strategic Redlines & Counter-Drafting Tab */}
            {activeTab === "negotiation" && (
              <div className="tab-redlines-container">
                <div style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", marginBottom: "16px" }}>
                  Multi-Tier Legal Counter-Drafting Playbook. Choose between Balanced, Protective, and Aggressive replacement language.
                </div>

                {analysisData?.risks && analysisData.risks.filter((r) => r.suggested_revision || r.suggestion).length > 0 ? (
                  analysisData.risks
                    .filter((r) => r.suggested_revision || r.suggestion)
                    .map((risk, idx) => {
                      const drafts = getRedlineDrafts(risk);
                      const currentTier = selectedRedlineTier[idx] || "balanced";
                      const activeReplacement =
                        currentTier === "balanced"
                          ? drafts.balanced
                          : currentTier === "protective"
                          ? drafts.protective
                          : drafts.aggressive;

                      return (
                        <div key={idx} className="redline-playbook-card">
                          <div className="redline-card-header">
                            <div className="redline-clause-name">
                              <strong>{risk.risk_type.replace(/_/g, " ")}</strong>
                              <span className="redline-badge">Playbook #{idx + 1}</span>
                            </div>

                            {/* Tier Selector Pills */}
                            <div className="tier-selector-pills">
                              <button
                                className={`tier-btn ${currentTier === "balanced" ? "active" : ""}`}
                                onClick={() => setSelectedRedlineTier((prev) => ({ ...prev, [idx]: "balanced" }))}
                              >
                                🛡️ Balanced
                              </button>
                              <button
                                className={`tier-btn ${currentTier === "protective" ? "active" : ""}`}
                                onClick={() => setSelectedRedlineTier((prev) => ({ ...prev, [idx]: "protective" }))}
                              >
                                ⚖️ Protective
                              </button>
                              <button
                                className={`tier-btn ${currentTier === "aggressive" ? "active" : ""}`}
                                onClick={() => setSelectedRedlineTier((prev) => ({ ...prev, [idx]: "aggressive" }))}
                              >
                                ⚡ Aggressive
                              </button>
                            </div>
                          </div>

                          {/* Side-by-Side Diff Layout */}
                          <div className="redline-diff-grid">
                            {/* Original Clause */}
                            <div className="diff-panel original">
                              <div className="diff-panel-title">
                                <span>ORIGINAL RISKY CLAUSE</span>
                                <button
                                  className="btn-copy-snippet"
                                  onClick={() => copyToClipboard(drafts.original, `orig-${idx}`)}
                                >
                                  {copyStatus === `orig-${idx}` ? "✓ Copied" : "Copy"}
                                </button>
                              </div>
                              <div className="diff-text-content">
                                "{drafts.original}"
                              </div>
                            </div>

                            {/* Counter-Draft Replacement */}
                            <div className="diff-panel replacement">
                              <div className="diff-panel-title">
                                <span>PROPOSED COUNTER-DRAFT ({currentTier.toUpperCase()})</span>
                                <button
                                  className="btn-copy-snippet"
                                  onClick={() => copyToClipboard(activeReplacement, `rep-${idx}`)}
                                >
                                  {copyStatus === `rep-${idx}` ? "✓ Copied!" : "Copy Replacement"}
                                </button>
                              </div>
                              <div className="diff-text-content highlight-replacement">
                                {activeReplacement}
                              </div>
                            </div>
                          </div>

                          {/* Negotiation Strategy Callout */}
                          {risk.negotiation_tip && (
                            <div className="negotiation-playbook-callout">
                              <div className="callout-title">🎯 Tactical Negotiation Strategy:</div>
                              <p className="callout-text">{risk.negotiation_tip}</p>
                            </div>
                          )}
                        </div>
                      );
                    })
                ) : (
                  <div style={{ textAlign: "center", padding: "48px 16px", color: "var(--color-text-muted)" }}>
                    <p>No redlines available. Run the analysis to generate multi-tier counter-drafts.</p>
                  </div>
                )}
              </div>
            )}

            {/* 5. Key Clauses Explorer Tab */}
            {activeTab === "clauses" && (
              <div className="clauses-container">
                <div className="clause-toolbar">
                  <div className="risk-search-box" style={{ flex: 1 }}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <input
                      type="text"
                      placeholder="Search extracted clauses..."
                      value={clauseSearch}
                      onChange={(e) => setClauseSearch(e.target.value)}
                    />
                  </div>

                  {clauseEntries.length > 0 && (
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button className="btn btn-secondary btn-xs" onClick={() => toggleAllClauses(true)}>
                        Expand All
                      </button>
                      <button className="btn btn-secondary btn-xs" onClick={() => toggleAllClauses(false)}>
                        Collapse All
                      </button>
                    </div>
                  )}
                </div>

                {clauseEntries.length > 0 ? (
                  clauseEntries.map(([key, val]: [string, any]) => {
                    const isExpanded = expandedClauses[key] ?? true;
                    const clauseText =
                      typeof val === "object" && val !== null
                        ? String(val.text || "Not mentioned in agreement")
                        : String(val || "Not mentioned in agreement");
                    const clauseLocation =
                      typeof val === "object" && val !== null ? val.location : null;

                    return (
                      <div key={key} className="clause-card">
                        <div className="clause-card-header" onClick={() => toggleClause(key)}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span className="clause-type-name">{key.replace(/_/g, " ")}</span>
                            {clauseLocation && clauseLocation !== "Not mentioned" && (
                              <span className="clause-location-tag">
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
                            <div style={{ whiteSpace: "pre-wrap" }}>{clauseText}</div>
                            <div style={{ marginTop: "10px", display: "flex", justifyContent: "flex-end" }}>
                              <button
                                className="btn-copy-snippet"
                                onClick={() => copyToClipboard(clauseText, `clause-${key}`)}
                              >
                                {copyStatus === `clause-${key}` ? "✓ Copied" : "Copy Clause"}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div style={{ textAlign: "center", padding: "48px 16px", color: "var(--color-text-muted)" }}>
                    <p>No clauses matching your search query.</p>
                  </div>
                )}
              </div>
            )}

            {/* 6. Document Raw Text Tab */}
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

                  <button className="btn btn-secondary btn-xs" onClick={() => copyToClipboard(rawText, "Full Text")}>
                    {copyStatus === "Full Text" ? "✓ Copied!" : "Copy Full Text"}
                  </button>
                </div>

                <div className="raw-text-viewer-box">
                  {rawText || "No text has been extracted from this document yet. Click Run AI Legal Analysis."}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
