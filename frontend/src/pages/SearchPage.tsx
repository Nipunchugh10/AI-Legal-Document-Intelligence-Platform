import React, { useState, useEffect } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import api from "../services/api";
import { useToast } from "../context/ToastContext";
import { SkeletonCard } from "../components/Skeleton";
import "./SearchPage.css";

export interface SearchChunkResult {
  chunk_index: number;
  text: string;
  similarity: number;
  highlighted_text?: string;
}

export interface ContractSearchResult {
  contract_id: number;
  filename: string;
  document_type?: string;
  risk_level?: string;
  risk_score?: number | null;
  created_at: string;
  status: string;
  max_similarity: number;
  match_count: number;
  matching_chunks: SearchChunkResult[];
}

export interface SemanticSearchResponse {
  query: string;
  total_contracts_matched: number;
  total_chunks_matched: number;
  results: ContractSearchResult[];
}

const POPULAR_SUGGESTIONS = [
  "Indemnification & Hold Harmless",
  "Unilateral Termination Without Cause",
  "Confidentiality & Trade Secrets",
  "Payment Terms & Milestones",
  "Non-Compete & Restrictive Covenants",
  "Governing Law & Arbitration",
  "Intellectual Property Assignment",
  "Liability Cap Exceptions",
];

const DOC_TYPES = [
  { label: "All Document Types", value: "" },
  { label: "Service Agreements", value: "Service" },
  { label: "NDAs & Confidentiality", value: "NDA" },
  { label: "Employment & Labour", value: "Employment" },
  { label: "Lease & Property", value: "Lease" },
  { label: "SaaS & Software License", value: "SaaS" },
];

const RISK_LEVELS = [
  { label: "All Risks", value: "" },
  { label: "Critical", value: "CRITICAL", class: "active-critical" },
  { label: "High", value: "HIGH", class: "active-high" },
  { label: "Medium", value: "MEDIUM", class: "active-medium" },
  { label: "Safe / Low", value: "SAFE", class: "active-safe" },
];

export const SearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { addToast } = useToast();

  // URL state synchronization
  const initialQuery = searchParams.get("q") || "";
  const initialDocType = searchParams.get("doc_type") || "";
  const initialRisk = searchParams.get("risk") || "";
  const initialMinSim = Number(searchParams.get("min_sim")) || 0;

  const [searchInput, setSearchInput] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);
  const [selectedDocType, setSelectedDocType] = useState(initialDocType);
  const [selectedRisk, setSelectedRisk] = useState(initialRisk);
  const [minSimilarity, setMinSimilarity] = useState(initialMinSim);
  const [copiedChunkKey, setCopiedChunkKey] = useState<string | null>(null);

  // Debounce input updates (350ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchInput.trim());
    }, 350);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Sync state to URL params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (debouncedQuery) params.q = debouncedQuery;
    if (selectedDocType) params.doc_type = selectedDocType;
    if (selectedRisk) params.risk = selectedRisk;
    if (minSimilarity > 0) params.min_sim = minSimilarity.toString();
    setSearchParams(params, { replace: true });
  }, [debouncedQuery, selectedDocType, selectedRisk, minSimilarity, setSearchParams]);

  // TanStack React Query for Semantic Search
  const {
    data: searchData,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery<SemanticSearchResponse>({
    queryKey: ["semantic-search", debouncedQuery, selectedDocType, selectedRisk, minSimilarity],
    queryFn: async () => {
      if (!debouncedQuery) {
        return {
          query: "",
          total_contracts_matched: 0,
          total_chunks_matched: 0,
          results: [],
        };
      }

      const params: Record<string, any> = {
        q: debouncedQuery,
        limit: 20,
      };
      if (selectedDocType) params.document_type = selectedDocType;
      if (selectedRisk) params.risk_level = selectedRisk;
      if (minSimilarity > 0) params.min_similarity = minSimilarity / 100;

      const response = await api.get<SemanticSearchResponse>("/contracts/search", { params });
      return response.data;
    },
    enabled: debouncedQuery.length > 0,
    staleTime: 60 * 1000,
  });

  const handleSuggestionClick = (query: string) => {
    setSearchInput(query);
    setDebouncedQuery(query);
  };

  const handleClear = () => {
    setSearchInput("");
    setDebouncedQuery("");
  };

  const handleResetFilters = () => {
    setSelectedDocType("");
    setSelectedRisk("");
    setMinSimilarity(0);
    addToast("Filters reset to default.", "info");
  };

  const copyToClipboard = (text: string, chunkKey: string) => {
    navigator.clipboard.writeText(text);
    setCopiedChunkKey(chunkKey);
    addToast("Clause excerpt copied to clipboard.", "success");
    setTimeout(() => setCopiedChunkKey(null), 2000);
  };

  const results = searchData?.results || [];

  return (
    <div className="search-page-container">
      {/* --- Top Search Control Card --- */}
      <section className="search-hero-card">
        <div className="search-header-text">
          <div className="badge-search-pill">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            Semantic Memory & Portfolio Intelligence
          </div>
          <h1 className="search-title">Cross-Contract Semantic Search</h1>
          <p className="search-subtitle">
            Query across your entire contract repository in natural language. Powered by vector
            embeddings and cosine similarity to find relevant obligations, liabilities, and fine print.
          </p>
        </div>

        {/* Big Search Input Field */}
        <div className="search-input-wrapper">
          <div className="search-input-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <input
            type="text"
            className="search-main-input"
            placeholder="Search clauses (e.g., 'unilateral termination', 'indemnity cap', 'non-compete duration')..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            autoFocus
          />
          <div className="search-input-actions">
            {isFetching && <div className="search-spinner" title="Searching..." />}
            {searchInput && (
              <button
                className="search-clear-btn"
                onClick={handleClear}
                title="Clear query"
                type="button"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Quick Suggestion Chips */}
        <div className="search-suggestions-row">
          <span className="suggestion-label">Suggested:</span>
          {POPULAR_SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              className="suggestion-chip"
              onClick={() => handleSuggestionClick(suggestion)}
              type="button"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </section>

      {/* --- Main Workspace (Filters Sidebar + Search Results) --- */}
      <div className="search-workspace-grid">
        {/* Left Filter Sidebar */}
        <aside className="search-filters-sidebar">
          <div className="filter-section-header">
            <span className="filter-section-title">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
              </svg>
              Filter Portfolio
            </span>
            {(selectedDocType || selectedRisk || minSimilarity > 0) && (
              <button className="btn-reset-filters" onClick={handleResetFilters} type="button">
                Reset All
              </button>
            )}
          </div>

          {/* Document Type Filter */}
          <div className="filter-group">
            <span className="filter-group-title">Document Type</span>
            <div className="filter-options-stack">
              {DOC_TYPES.map((dt) => (
                <button
                  key={dt.value}
                  className={`filter-option-btn ${selectedDocType === dt.value ? "active" : ""}`}
                  onClick={() => setSelectedDocType(dt.value)}
                  type="button"
                >
                  <span>{dt.label}</span>
                  {selectedDocType === dt.value && <span>✓</span>}
                </button>
              ))}
            </div>
          </div>

          {/* Risk Level Filter */}
          <div className="filter-group">
            <span className="filter-group-title">Risk Exposure Tier</span>
            <div className="risk-filter-grid">
              {RISK_LEVELS.map((rl) => {
                const isActive = selectedRisk === rl.value;
                const activeClass = isActive ? (rl.class || "active-generic") : "";
                return (
                  <button
                    key={rl.value}
                    className={`risk-filter-btn ${activeClass}`}
                    onClick={() => setSelectedRisk(rl.value)}
                    type="button"
                  >
                    {rl.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Minimum Similarity Threshold Slider */}
          <div className="filter-group">
            <div className="similarity-slider-box">
              <div className="similarity-slider-header">
                <span>Minimum Match Quality</span>
                <span className="slider-value">{minSimilarity}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="90"
                step="5"
                value={minSimilarity}
                onChange={(e) => setMinSimilarity(Number(e.target.value))}
                className="similarity-range-input"
              />
            </div>
          </div>
        </aside>

        {/* Right Search Results Area */}
        <main className="search-results-area">
          {/* Results Summary Bar */}
          {debouncedQuery && !isLoading && (
            <div className="results-summary-bar">
              <span className="summary-stats-badge">
                Found <strong>{searchData?.total_contracts_matched || 0}</strong> contracts (
                <strong>{searchData?.total_chunks_matched || 0}</strong> relevant excerpts) for &ldquo;
                {debouncedQuery}&rdquo;
              </span>
              <span className="results-sort-tag">Ranked by Cosine Relevance</span>
            </div>
          )}

          {/* Loading Skeleton State */}
          {isLoading && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          )}

          {/* Initial State Prompt */}
          {!debouncedQuery && !isLoading && (
            <div className="search-empty-state">
              <div className="empty-state-icon">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>
              <h3 className="empty-state-title">Ready to Search Your Legal Vault</h3>
              <p className="empty-state-desc">
                Type any legal topic, clause type, obligation, or risk term in the search bar above,
                or click one of the suggested query chips to start exploring your documents.
              </p>
            </div>
          )}

          {/* Error State */}
          {isError && (
            <div className="search-empty-state" style={{ borderColor: "rgba(239, 68, 68, 0.3)" }}>
              <h3 className="empty-state-title" style={{ color: "#f87171" }}>
                Search Query Failed
              </h3>
              <p className="empty-state-desc">
                {(error as any)?.response?.data?.detail ||
                  "Unable to execute vector search. Please check your backend connection."}
              </p>
              <button
                className="btn btn-primary"
                onClick={() => refetch()}
                style={{ marginTop: "12px" }}
              >
                Retry Search
              </button>
            </div>
          )}

          {/* No Results Found State */}
          {debouncedQuery && !isLoading && !isError && results.length === 0 && (
            <div className="search-empty-state">
              <div className="empty-state-icon" style={{ color: "#94a3b8" }}>
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="9" y1="15" x2="15" y2="15" />
                </svg>
              </div>
              <h3 className="empty-state-title">No Matching Clauses Found</h3>
              <p className="empty-state-desc">
                No contract excerpts matched your query &ldquo;{debouncedQuery}&rdquo; with the current
                filters. Try broadening your keywords, clearing filters, or lowering the minimum match
                quality threshold.
              </p>
              {(selectedDocType || selectedRisk || minSimilarity > 0) && (
                <button
                  className="btn btn-secondary"
                  onClick={handleResetFilters}
                  style={{ marginTop: "12px" }}
                >
                  Clear Active Filters
                </button>
              )}
            </div>
          )}

          {/* Results List */}
          {debouncedQuery && !isLoading && results.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              {results.map((contract) => {
                const matchPercent = Math.round(contract.max_similarity * 100);
                const riskClass = contract.risk_level
                  ? `risk-${contract.risk_level.toLowerCase()}`
                  : "risk-low";

                return (
                  <article key={contract.contract_id} className="contract-search-card">
                    {/* Card Top Header */}
                    <div className="card-top-header">
                      <div className="card-title-group">
                        <div className="doc-file-icon">
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="22"
                            height="22"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                          >
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                          </svg>
                        </div>
                        <div>
                          <Link
                            to={`/contracts/${contract.contract_id}`}
                            className="contract-name-link"
                          >
                            {contract.filename}
                          </Link>
                          <div className="contract-meta-row">
                            <span className="doctype-tag">{contract.document_type}</span>
                            {contract.risk_level && contract.risk_level !== "UNKNOWN" && (
                              <span className={`risk-tag ${riskClass}`}>
                                {contract.risk_level} Risk
                                {contract.risk_score !== null && ` (${contract.risk_score}/100)`}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Match Score Badge */}
                      <div className="match-score-pill">
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                        >
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                          <polyline points="22 4 12 14.01 9 11.01" />
                        </svg>
                        {matchPercent}% Match
                      </div>
                    </div>

                    {/* Excerpts / Matching Chunks */}
                    <div className="matching-chunks-stack">
                      {contract.matching_chunks.map((chunk) => {
                        const chunkKey = `${contract.contract_id}-${chunk.chunk_index}`;
                        const isCopied = copiedChunkKey === chunkKey;
                        const chunkMatchPercent = Math.round(chunk.similarity * 100);

                        return (
                          <div key={chunk.chunk_index} className="chunk-excerpt-box">
                            <div className="chunk-header-meta">
                              <span>
                                Chunk #{chunk.chunk_index + 1} &bull; {chunkMatchPercent}% semantic similarity
                              </span>
                              <button
                                className="btn-copy-chunk"
                                onClick={() => copyToClipboard(chunk.text, chunkKey)}
                                type="button"
                              >
                                {isCopied ? "✓ Copied!" : "Copy Passage"}
                              </button>
                            </div>
                            <div
                              className="chunk-text-body"
                              dangerouslySetInnerHTML={{
                                __html: chunk.highlighted_text || chunk.text,
                              }}
                            />
                          </div>
                        );
                      })}
                    </div>

                    {/* Card Actions Footer */}
                    <div className="card-action-footer">
                      <span style={{ fontSize: "0.8rem", color: "var(--color-text-muted, #94a3b8)" }}>
                        {contract.match_count} total clause match{contract.match_count > 1 ? "es" : ""} found
                      </span>
                      <div className="footer-btn-group">
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => navigate(`/contracts/${contract.contract_id}/ask`)}
                        >
                          Ask AI About This
                        </button>
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => navigate(`/contracts/${contract.contract_id}`)}
                        >
                          Open Contract Workspace &rarr;
                        </button>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default SearchPage;
