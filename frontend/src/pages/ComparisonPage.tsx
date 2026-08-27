import React, { useState, useEffect, useMemo, useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import api from "../services/api";
import { useToast } from "../context/ToastContext";
import { SkeletonCard, SkeletonTable } from "../components/Skeleton";
import type { Contract } from "../store/useContractStore";
import "./ComparisonPage.css";

interface DiffSegment {
  operation: "equal" | "insert" | "delete" | "replace";
  text: string;
}

interface ClauseDiffItem {
  clause_key: string;
  clause_title: string;
  status: "ADDED" | "REMOVED" | "MODIFIED" | "UNCHANGED";
  base_text: string | null;
  target_text: string | null;
  similarity_ratio: number;
  diff_segments: DiffSegment[];
}

interface RiskProfileDelta {
  base_risk_score: number;
  target_risk_score: number;
  score_delta: number;
  base_red_flags: number;
  target_red_flags: number;
  base_yellow_flags: number;
  target_yellow_flags: number;
  base_green_flags: number;
  target_green_flags: number;
  assessment: string;
}

interface ComparisonMetrics {
  clauses_added_count: number;
  clauses_removed_count: number;
  clauses_modified_count: number;
  clauses_unchanged_count: number;
  base_word_count: number;
  target_word_count: number;
  similarity_percentage: number;
}

interface ComparisonResponse {
  base_contract_id: number;
  base_filename: string;
  target_contract_id: number;
  target_filename: string;
  summary: string;
  metrics: ComparisonMetrics;
  clause_diffs: ClauseDiffItem[];
  risk_delta: RiskProfileDelta;
}

export const ComparisonPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const toast = useToast();

  const [contracts, setContracts] = useState<Contract[]>([]);
  const [isLoadingContracts, setIsLoadingContracts] = useState(true);
  const [baseId, setBaseId] = useState<number | "">("");
  const [targetId, setTargetId] = useState<number | "">("");
  const [isComparing, setIsComparing] = useState(false);
  const [comparisonData, setComparisonData] = useState<ComparisonResponse | null>(null);

  // Filters
  const [selectedFilter, setSelectedFilter] = useState<"ALL" | "MODIFIED" | "ADDED" | "REMOVED" | "UNCHANGED">("ALL");
  const [clauseSearch, setClauseSearch] = useState("");

  // Load contracts from vault
  useEffect(() => {
    setIsLoadingContracts(true);
    api
      .get<Contract[]>("/contracts/")
      .then((res) => {
        setContracts(res.data);
        // Check URL params
        const urlBase = searchParams.get("base");
        const urlTarget = searchParams.get("target");
        if (urlBase && !isNaN(Number(urlBase))) {
          setBaseId(Number(urlBase));
        }
        if (urlTarget && !isNaN(Number(urlTarget))) {
          setTargetId(Number(urlTarget));
        }
      })
      .catch((err) => {
        console.error("Failed to load contracts:", err);
        toast.error("Failed to load contracts from vault.");
      })
      .finally(() => setIsLoadingContracts(false));
  }, [searchParams, toast]);

  // Execute comparison
  const handleCompare = useCallback(
    async (bId?: number, tId?: number) => {
      const activeBaseId = bId || (baseId as number);
      const activeTargetId = tId || (targetId as number);

      if (!activeBaseId || !activeTargetId) {
        toast.warning("Please select both a baseline and a comparison contract.");
        return;
      }
      if (activeBaseId === activeTargetId) {
        toast.warning("Please select two distinct contracts to compare.");
        return;
      }

      setIsComparing(true);
      setSearchParams({ base: String(activeBaseId), target: String(activeTargetId) });

      try {
        const res = await api.post<ComparisonResponse>("/contracts/compare", {
          base_contract_id: activeBaseId,
          target_contract_id: activeTargetId,
        });
        setComparisonData(res.data);
        toast.success(`Successfully compared "${res.data.base_filename}" vs "${res.data.target_filename}"`);
      } catch (err: any) {
        console.error("Comparison failed:", err);
        const errMsg = err?.response?.data?.detail || "Failed to compare contract versions.";
        toast.error(errMsg);
      } finally {
        setIsComparing(false);
      }
    },
    [baseId, targetId, setSearchParams, toast]
  );

  // Auto-trigger if URL has both params and contracts are loaded
  useEffect(() => {
    const urlBase = searchParams.get("base");
    const urlTarget = searchParams.get("target");
    if (urlBase && urlTarget && contracts.length > 0 && !comparisonData && !isComparing) {
      const b = Number(urlBase);
      const t = Number(urlTarget);
      if (b && t && b !== t) {
        handleCompare(b, t);
      }
    }
  }, [contracts, searchParams, comparisonData, isComparing, handleCompare]);

  // Swap baseline and target
  const handleSwap = () => {
    const prevBase = baseId;
    const prevTarget = targetId;
    setBaseId(prevTarget);
    setTargetId(prevBase);
    if (prevTarget && prevBase) {
      handleCompare(prevTarget as number, prevBase as number);
    }
  };

  // Filtered clauses
  const filteredClauses = useMemo(() => {
    if (!comparisonData) return [];
    return comparisonData.clause_diffs.filter((item) => {
      const matchesFilter =
        selectedFilter === "ALL" || item.status === selectedFilter;
      const matchesSearch =
        !clauseSearch.trim() ||
        item.clause_title.toLowerCase().includes(clauseSearch.toLowerCase()) ||
        (item.base_text && item.base_text.toLowerCase().includes(clauseSearch.toLowerCase())) ||
        (item.target_text && item.target_text.toLowerCase().includes(clauseSearch.toLowerCase()));
      return matchesFilter && matchesSearch;
    });
  }, [comparisonData, selectedFilter, clauseSearch]);

  // Export full Markdown comparison report
  const handleExportReport = () => {
    if (!comparisonData) return;

    const lines: string[] = [];
    lines.push(`# Multi-Version Contract Comparison Report`);
    lines.push(`**Generated on:** ${new Date().toLocaleString()}`);
    lines.push(`**Baseline Contract (V1):** ${comparisonData.base_filename} (ID #${comparisonData.base_contract_id})`);
    lines.push(`**Target Contract (V2):** ${comparisonData.target_filename} (ID #${comparisonData.target_contract_id})`);
    lines.push(`\n---\n`);

    lines.push(`## 1. Executive Change Summary`);
    lines.push(comparisonData.summary);
    lines.push(`\n---\n`);

    lines.push(`## 2. Quantitative Change Metrics`);
    lines.push(`- **Overall Text Similarity:** ${comparisonData.metrics.similarity_percentage}%`);
    lines.push(`- **Modified Clauses:** ${comparisonData.metrics.clauses_modified_count}`);
    lines.push(`- **Added Clauses:** ${comparisonData.metrics.clauses_added_count}`);
    lines.push(`- **Removed Clauses:** ${comparisonData.metrics.clauses_removed_count}`);
    lines.push(`- **Unchanged Clauses:** ${comparisonData.metrics.clauses_unchanged_count}`);
    lines.push(`- **Baseline Word Count:** ${comparisonData.metrics.base_word_count} words`);
    lines.push(`- **Target Word Count:** ${comparisonData.metrics.target_word_count} words`);
    lines.push(`\n---\n`);

    lines.push(`## 3. Risk Profile & Exposure Evolution`);
    lines.push(`- **Baseline Risk Score:** ${comparisonData.risk_delta.base_risk_score} / 100`);
    lines.push(`- **Target Risk Score:** ${comparisonData.risk_delta.target_risk_score} / 100`);
    lines.push(`- **Score Delta:** ${comparisonData.risk_delta.score_delta > 0 ? "+" : ""}${comparisonData.risk_delta.score_delta} points`);
    lines.push(`- **Critical Red Flags:** ${comparisonData.risk_delta.base_red_flags} (Base) $\\rightarrow$ ${comparisonData.risk_delta.target_red_flags} (Target)`);
    lines.push(`- **Moderate Concerns:** ${comparisonData.risk_delta.base_yellow_flags} (Base) $\\rightarrow$ ${comparisonData.risk_delta.target_yellow_flags} (Target)`);
    lines.push(`- **Protective Provisions:** ${comparisonData.risk_delta.base_green_flags} (Base) $\\rightarrow$ ${comparisonData.risk_delta.target_green_flags} (Target)`);
    lines.push(`- **Counsel Assessment:** ${comparisonData.risk_delta.assessment}`);
    lines.push(`\n---\n`);

    lines.push(`## 4. Detailed Clause-Level Deltas`);
    comparisonData.clause_diffs.forEach((c, idx) => {
      lines.push(`### ${idx + 1}. ${c.clause_title} [${c.status}]`);
      lines.push(`- **Similarity Score:** ${(c.similarity_ratio * 100).toFixed(1)}%`);
      if (c.base_text) {
        lines.push(`\n**Original Baseline Clause (V1):**\n> ${c.base_text}\n`);
      }
      if (c.target_text) {
        lines.push(`\n**Revised Counter-Draft Clause (V2):**\n> ${c.target_text}\n`);
      }
      lines.push(`\n`);
    });

    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Contract_Comparison_${comparisonData.base_contract_id}_vs_${comparisonData.target_contract_id}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    toast.success("Comparison report downloaded successfully!");
  };

  // Helper to render diff segments
  const renderDiffContent = (segments: DiffSegment[]) => {
    return (
      <div className="diff-inline-view">
        {segments.map((seg, i) => {
          if (seg.operation === "equal") {
            return <span key={i} className="diff-segment equal">{seg.text}</span>;
          }
          if (seg.operation === "delete") {
            return <del key={i} className="diff-segment delete">{seg.text}</del>;
          }
          if (seg.operation === "insert") {
            return <ins key={i} className="diff-segment insert">{seg.text}</ins>;
          }
          return <span key={i}>{seg.text}</span>;
        })}
      </div>
    );
  };

  return (
    <div className="comparison-page-container">
      {/* --- Top Control Bar: Select Contracts --- */}
      <div className="comparison-control-card">
        <div className="control-header">
          <div className="badge-comparison-pill">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M16 3h5v5" />
              <path d="M8 3H3v5" />
              <path d="M21 3l-7 7" />
              <path d="M3 3l7 7" />
              <path d="M16 21h5v-5" />
              <path d="M8 21H3v-5" />
              <path d="M21 21l-7-7" />
              <path d="M3 21l7-7" />
            </svg>
            Multi-Version Legal Diff Engine
          </div>
          <h1 className="comparison-title">Side-by-Side Contract Comparison</h1>
          <p className="comparison-subtitle">
            Compare drafts, revisions, or counter-party redlines. Detect added liabilities, removed protections, modified covenants, and risk evolution.
          </p>
        </div>

        <div className="selectors-grid">
          {/* Base Contract Selector */}
          <div className="selector-group">
            <label className="selector-label">
              <span className="step-tag base">V1</span>
              <span>Baseline Contract (Original)</span>
            </label>
            <select
              className="selector-dropdown"
              value={baseId}
              onChange={(e) => setBaseId(e.target.value ? Number(e.target.value) : "")}
              disabled={isLoadingContracts || isComparing}
            >
              <option value="">Select original contract...</option>
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.filename} (ID #{c.id})
                </option>
              ))}
            </select>
          </div>

          {/* Swap Button */}
          <button
            className="btn-swap-contracts"
            onClick={handleSwap}
            disabled={!baseId || !targetId || isComparing}
            title="Swap Baseline and Target"
            aria-label="Swap Contracts"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="16 3 21 3 21 8" />
              <line x1="4" y1="20" x2="21" y2="3" />
              <polyline points="21 16 21 21 16 21" />
              <line x1="15" y1="15" x2="21" y2="21" />
              <line x1="4" y1="4" x2="9" y2="9" />
            </svg>
          </button>

          {/* Target Contract Selector */}
          <div className="selector-group">
            <label className="selector-label">
              <span className="step-tag target">V2</span>
              <span>Comparison Contract (Revision)</span>
            </label>
            <select
              className="selector-dropdown"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value ? Number(e.target.value) : "")}
              disabled={isLoadingContracts || isComparing}
            >
              <option value="">Select revised contract...</option>
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.filename} (ID #{c.id})
                </option>
              ))}
            </select>
          </div>

          {/* Compare Action Button */}
          <button
            className="btn btn-primary btn-run-comparison"
            onClick={() => handleCompare()}
            disabled={!baseId || !targetId || baseId === targetId || isComparing}
          >
            {isComparing ? (
              <>
                <div className="spinner spinner-sm" />
                <span>Diffing Versions...</span>
              </>
            ) : (
              <>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
                <span>Compare Versions</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* --- Loading Skeleton State --- */}
      {isComparing && (
        <div className="comparison-loading-container">
          <SkeletonCard rows={2} />
          <div style={{ marginTop: "20px" }}>
            <SkeletonTable rows={4} columns={3} />
          </div>
        </div>
      )}

      {/* --- Comparison Active Viewport --- */}
      {!isComparing && comparisonData && (
        <div className="comparison-results-viewport">
          {/* Executive Summary & Export Card */}
          <div className="summary-banner-card">
            <div className="summary-text-wrapper">
              <div className="summary-badge-row">
                <span className="summary-tag">Executive Synthesis</span>
                <span className="similarity-pill">
                  🎯 {comparisonData.metrics.similarity_percentage}% Overall Similarity
                </span>
              </div>
              <p className="summary-narrative">{comparisonData.summary}</p>
            </div>
            <button className="btn btn-secondary btn-export-diff" onClick={handleExportReport}>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              <span>Export Diff Report (.md)</span>
            </button>
          </div>

          {/* Metrics & Risk Evolution Dual Grid */}
          <div className="metrics-risk-grid">
            {/* 4 Quantitative Change Metrics */}
            <div className="change-metrics-card">
              <h3 className="card-section-title">Clause Change Metrics</h3>
              <div className="metrics-four-grid">
                <div className="metric-tile modified">
                  <div className="metric-count">{comparisonData.metrics.clauses_modified_count}</div>
                  <div className="metric-name">Modified Clauses</div>
                </div>
                <div className="metric-tile added">
                  <div className="metric-count">+{comparisonData.metrics.clauses_added_count}</div>
                  <div className="metric-name">Added Clauses</div>
                </div>
                <div className="metric-tile removed">
                  <div className="metric-count">-{comparisonData.metrics.clauses_removed_count}</div>
                  <div className="metric-name">Removed Clauses</div>
                </div>
                <div className="metric-tile unchanged">
                  <div className="metric-count">{comparisonData.metrics.clauses_unchanged_count}</div>
                  <div className="metric-name">Unchanged Clauses</div>
                </div>
              </div>
            </div>

            {/* Risk Profile Shift Gauge */}
            <div className="risk-evolution-card">
              <div className="risk-evolution-header">
                <h3 className="card-section-title">Risk Profile Evolution</h3>
                <span className={`risk-shift-badge ${comparisonData.risk_delta.score_delta <= 0 ? "favorable" : "critical"}`}>
                  {comparisonData.risk_delta.score_delta <= 0 ? "🛡️ Favorable Shift" : "⚠️ Increased Exposure"}
                </span>
              </div>

              <div className="risk-score-comparison">
                <div className="score-box base">
                  <span className="score-label">Baseline Score</span>
                  <div className="score-num">{comparisonData.risk_delta.base_risk_score}</div>
                  <span className="score-subtext">/100 exposure</span>
                </div>
                <div className="score-arrow-delta">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                  <span className={`delta-val ${comparisonData.risk_delta.score_delta <= 0 ? "neg" : "pos"}`}>
                    {comparisonData.risk_delta.score_delta > 0 ? "+" : ""}
                    {comparisonData.risk_delta.score_delta} pts
                  </span>
                </div>
                <div className="score-box target">
                  <span className="score-label">Target Score</span>
                  <div className="score-num">{comparisonData.risk_delta.target_risk_score}</div>
                  <span className="score-subtext">/100 exposure</span>
                </div>
              </div>

              <div className="risk-flags-side-by-side">
                <div className="flag-row">
                  <span className="flag-dot red" />
                  <span className="flag-label">Red Flags (Critical):</span>
                  <span className="flag-values">
                    {comparisonData.risk_delta.base_red_flags} → <strong>{comparisonData.risk_delta.target_red_flags}</strong>
                  </span>
                </div>
                <div className="flag-row">
                  <span className="flag-dot yellow" />
                  <span className="flag-label">Yellow Flags (Concerns):</span>
                  <span className="flag-values">
                    {comparisonData.risk_delta.base_yellow_flags} → <strong>{comparisonData.risk_delta.target_yellow_flags}</strong>
                  </span>
                </div>
                <div className="flag-row">
                  <span className="flag-dot green" />
                  <span className="flag-label">Green Flags (Protective):</span>
                  <span className="flag-values">
                    {comparisonData.risk_delta.base_green_flags} → <strong>{comparisonData.risk_delta.target_green_flags}</strong>
                  </span>
                </div>
              </div>

              <p className="risk-assessment-narrative">{comparisonData.risk_delta.assessment}</p>
            </div>
          </div>

          {/* --- Clause Difference List & Filter Bar --- */}
          <div className="clause-diffs-section">
            <div className="diffs-filter-bar">
              <div className="filter-tabs">
                <button
                  className={`tab-btn ${selectedFilter === "ALL" ? "active" : ""}`}
                  onClick={() => setSelectedFilter("ALL")}
                >
                  All Clauses ({comparisonData.clause_diffs.length})
                </button>
                <button
                  className={`tab-btn modified ${selectedFilter === "MODIFIED" ? "active" : ""}`}
                  onClick={() => setSelectedFilter("MODIFIED")}
                >
                  Modified ({comparisonData.metrics.clauses_modified_count})
                </button>
                <button
                  className={`tab-btn added ${selectedFilter === "ADDED" ? "active" : ""}`}
                  onClick={() => setSelectedFilter("ADDED")}
                >
                  Added (+{comparisonData.metrics.clauses_added_count})
                </button>
                <button
                  className={`tab-btn removed ${selectedFilter === "REMOVED" ? "active" : ""}`}
                  onClick={() => setSelectedFilter("REMOVED")}
                >
                  Removed (-{comparisonData.metrics.clauses_removed_count})
                </button>
                <button
                  className={`tab-btn unchanged ${selectedFilter === "UNCHANGED" ? "active" : ""}`}
                  onClick={() => setSelectedFilter("UNCHANGED")}
                >
                  Unchanged ({comparisonData.metrics.clauses_unchanged_count})
                </button>
              </div>

              <div className="diff-search-box">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <input
                  type="text"
                  placeholder="Filter clauses by title or text..."
                  value={clauseSearch}
                  onChange={(e) => setClauseSearch(e.target.value)}
                />
              </div>
            </div>

            {/* List of Clause Difference Cards */}
            <div className="clause-cards-list">
              {filteredClauses.length > 0 ? (
                filteredClauses.map((clause) => (
                  <div key={clause.clause_key} className={`clause-diff-card ${clause.status.toLowerCase()}`}>
                    <div className="clause-card-topbar">
                      <div className="clause-title-group">
                        <span className={`status-pill ${clause.status.toLowerCase()}`}>
                          {clause.status}
                        </span>
                        <h4 className="clause-title-text">{clause.clause_title}</h4>
                      </div>
                      <div className="clause-similarity-tag">
                        <span>Match: {(clause.similarity_ratio * 100).toFixed(0)}%</span>
                      </div>
                    </div>

                    {/* Side-by-side or Diff View */}
                    {clause.status === "MODIFIED" ? (
                      <div className="modified-clause-body">
                        <div className="diff-token-display">
                          <div className="diff-pane-label">Inline Visual Diff:</div>
                          {renderDiffContent(clause.diff_segments)}
                        </div>

                        <div className="side-by-side-clause-grid">
                          <div className="clause-subpane base">
                            <div className="subpane-header">
                              <span>Baseline (V1)</span>
                              <button
                                className="btn-copy-clause"
                                onClick={() => {
                                  if (clause.base_text) {
                                    navigator.clipboard.writeText(clause.base_text);
                                    toast.info("Baseline clause copied!");
                                  }
                                }}
                              >
                                Copy
                              </button>
                            </div>
                            <div className="subpane-text">{clause.base_text}</div>
                          </div>

                          <div className="clause-subpane target">
                            <div className="subpane-header">
                              <span>Revision (V2)</span>
                              <button
                                className="btn-copy-clause"
                                onClick={() => {
                                  if (clause.target_text) {
                                    navigator.clipboard.writeText(clause.target_text);
                                    toast.info("Revised clause copied!");
                                  }
                                }}
                              >
                                Copy
                              </button>
                            </div>
                            <div className="subpane-text">{clause.target_text}</div>
                          </div>
                        </div>
                      </div>
                    ) : clause.status === "ADDED" ? (
                      <div className="added-clause-body">
                        <div className="clause-subpane target">
                          <div className="subpane-header">
                            <span>Newly Added Clause in Revision (V2)</span>
                            <button
                              className="btn-copy-clause"
                              onClick={() => {
                                if (clause.target_text) {
                                  navigator.clipboard.writeText(clause.target_text);
                                  toast.info("Added clause copied!");
                                }
                              }}
                            >
                              Copy
                            </button>
                          </div>
                          <div className="subpane-text">{clause.target_text}</div>
                        </div>
                      </div>
                    ) : clause.status === "REMOVED" ? (
                      <div className="removed-clause-body">
                        <div className="clause-subpane base">
                          <div className="subpane-header">
                            <span>Removed Clause from Baseline (V1)</span>
                            <button
                              className="btn-copy-clause"
                              onClick={() => {
                                if (clause.base_text) {
                                  navigator.clipboard.writeText(clause.base_text);
                                  toast.info("Removed clause copied!");
                                }
                              }}
                            >
                              Copy
                            </button>
                          </div>
                          <div className="subpane-text">{clause.base_text}</div>
                        </div>
                      </div>
                    ) : (
                      <div className="unchanged-clause-body">
                        <div className="subpane-text unchanged-text">{clause.target_text}</div>
                      </div>
                    )}
                  </div>
                ))
              ) : (
                <div className="empty-filter-state">
                  <p>No clauses match the current filter or search criteria.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --- Empty Initial State --- */}
      {!isComparing && !comparisonData && (
        <div className="comparison-empty-hero">
          <div className="empty-hero-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M16 3h5v5" />
              <path d="M8 3H3v5" />
              <path d="M21 3l-7 7" />
              <path d="M3 3l7 7" />
              <path d="M16 21h5v-5" />
              <path d="M8 21H3v-5" />
              <path d="M21 21l-7-7" />
              <path d="M3 21l7-7" />
            </svg>
          </div>
          <h3>Select Two Contracts to Start Multi-Version Diffing</h3>
          <p>
            Choose a baseline original contract and a counter-draft revision from the dropdowns above to analyze clause modifications, additions, omissions, and risk exposure shifts.
          </p>
        </div>
      )}
    </div>
  );
};
