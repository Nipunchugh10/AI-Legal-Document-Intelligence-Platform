import React, { useState, useMemo } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "../services/api";
import { useContractStore, type Contract } from "../store/useContractStore";
import { useAuthStore } from "../store/useAuthStore";
import "./Dashboard.css";

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Zustand Store
  const setContractsInStore = useContractStore((state) => state.setContracts);
  const searchQuery = useContractStore((state) => state.searchQuery);
  const setSearchQuery = useContractStore((state) => state.setSearchQuery);
  const filterStatus = useContractStore((state) => state.filterStatus);
  const setFilterStatus = useContractStore((state) => state.setFilterStatus);
  const removeContractFromStore = useContractStore((state) => state.removeContract);

  // User state for tenant isolation
  const user = useAuthStore((state) => state.user);

  // Local View States
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [sortBy, setSortBy] = useState<"newest" | "oldest" | "name-asc" | "name-desc">("newest");
  const [contractToDelete, setContractToDelete] = useState<Contract | null>(null);

  // TanStack React Query: Fetch Contracts (Strictly Isolated per User)
  const {
    data: contracts = [],
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<Contract[]>({
    queryKey: ["contracts", user?.id],
    queryFn: async () => {
      if (!user?.id) return [];
      const response = await api.get<Contract[]>("/contracts/");
      setContractsInStore(response.data);
      return response.data;
    },
    enabled: !!user?.id,
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasProcessing = Array.isArray(data) && data.some((c) => c.status === "processing" || c.status === "pending");
      return hasProcessing ? 3000 : false;
    },
  });

  // TanStack React Query: Delete Contract Mutation
  const deleteMutation = useMutation({
    mutationFn: async (contractId: number) => {
      await api.delete(`/contracts/${contractId}`);
      return contractId;
    },
    onSuccess: (deletedId) => {
      removeContractFromStore(deletedId);
      queryClient.invalidateQueries({ queryKey: ["contracts", user?.id] });
      setContractToDelete(null);
    },
    onError: (err: any) => {
      alert(
        err.response?.data?.detail ||
          "Failed to delete contract. Please check your connection and try again."
      );
    },
  });

  // Derived Metrics
  const totalCount = contracts.length;
  const analyzedCount = contracts.filter(
    (c) => c.status === "analyzed" || (c.status as any) === "parsed"
  ).length;
  const pendingCount = contracts.filter(
    (c) => c.status === "pending" || c.status === "ingested"
  ).length;
  const failedCount = contracts.filter((c) => c.status === "failed").length;

  // Filter & Sort Logic
  const processedContracts = useMemo(() => {
    return contracts
      .filter((contract) => {
        // 1. Status filter
        if (filterStatus !== "all") {
          if (filterStatus === "analyzed") {
            if (contract.status !== "analyzed" && (contract.status as any) !== "parsed")
              return false;
          } else if (contract.status !== filterStatus) {
            return false;
          }
        }
        // 2. Search query filter (filename or document type)
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchesName = contract.filename.toLowerCase().includes(q);
          const matchesDocType = contract.document_type?.toLowerCase().includes(q);
          return matchesName || matchesDocType;
        }
        return true;
      })
      .sort((a, b) => {
        if (sortBy === "newest") {
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        }
        if (sortBy === "oldest") {
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        }
        if (sortBy === "name-asc") {
          return a.filename.localeCompare(b.filename);
        }
        if (sortBy === "name-desc") {
          return b.filename.localeCompare(a.filename);
        }
        return 0;
      });
  }, [contracts, filterStatus, searchQuery, sortBy]);

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const getDocTypeIcon = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    if (ext === "pdf") return "PDF";
    if (ext === "docx" || ext === "doc") return "DOCX";
    if (["png", "jpg", "jpeg", "webp"].includes(ext || "")) return "SCAN";
    return "DOC";
  };

  return (
    <div className="dashboard-page-container">
      {/* ── 1. Top Header & Title Bar ────────────────────────────────────────── */}
      <section className="vault-header-row">
        <div className="vault-title-group">
          <h1>Contract Vault</h1>
          <p>
            Central intelligence repository for your legal agreements, compliance scans, and
            negotiation playbooks.
          </p>
        </div>

        <div className="vault-header-actions">
          <button
            onClick={() => refetch()}
            className="btn btn-secondary"
            title="Refresh contracts list"
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
              <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
              <path d="M21 3v5h-5" />
              <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
              <path d="M8 16H3v5" />
            </svg>
            Sync Vault
          </button>

          <Link to="/contracts/upload" className="btn btn-primary">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            Upload Contract
          </Link>
        </div>
      </section>

      {/* ── 2. Portfolio Metrics Overview ────────────────────────────────────── */}
      <section className="vault-metrics-grid">
        <div className="metric-card">
          <div className="metric-icon-box metric-icon-primary">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <div className="metric-content">
            <span className="metric-label">Total Documents</span>
            <span className="metric-value">{isLoading ? "-" : totalCount}</span>
            <span className="metric-trend">Ingested in Vault</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box metric-icon-success">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
          </div>
          <div className="metric-content">
            <span className="metric-label">AI Analyzed</span>
            <span className="metric-value">{isLoading ? "-" : analyzedCount}</span>
            <span className="metric-trend">Full Dialectic Verified</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box metric-icon-warning">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div className="metric-content">
            <span className="metric-label">Pending Review</span>
            <span className="metric-value">{isLoading ? "-" : pendingCount}</span>
            <span className="metric-trend">Ready for Agent Analysis</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-icon-box metric-icon-accent">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <div className="metric-content">
            <span className="metric-label">Vault Security</span>
            <span className="metric-value">Active</span>
            <span className="metric-trend">SHA-256 OTP Encrypted</span>
          </div>
        </div>
      </section>

      {/* ── Quick AI Semantic Search Trigger Banner ─────────────────────── */}
      <div className="vault-search-jump-banner" onClick={() => navigate("/search")}>
        <div className="search-jump-left">
          <div className="search-jump-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
            >
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
          </div>
          <div>
            <span className="search-jump-title">AI Semantic Clause & Obligation Search</span>
            <span className="search-jump-desc">
              Find indemnity caps, non-competes, or hidden liability traps across all contracts using natural language
            </span>
          </div>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={(e) => {
            e.stopPropagation();
            navigate("/search");
          }}
          type="button"
        >
          Open Semantic Search &rarr;
        </button>
      </div>

      {/* ── 3. Control & Filter Toolbar ────────────────────────────────────── */}
      <section className="vault-control-bar">
        {/* Status Filter Pills */}
        <div className="vault-filter-pills">
          <button
            className={`filter-pill ${filterStatus === "all" ? "active" : ""}`}
            onClick={() => setFilterStatus("all")}
          >
            All <span className="filter-pill-count">{totalCount}</span>
          </button>
          <button
            className={`filter-pill ${filterStatus === "analyzed" ? "active" : ""}`}
            onClick={() => setFilterStatus("analyzed")}
          >
            Analyzed <span className="filter-pill-count">{analyzedCount}</span>
          </button>
          <button
            className={`filter-pill ${filterStatus === "ingested" ? "active" : ""}`}
            onClick={() => setFilterStatus("ingested")}
          >
            Ingested{" "}
            <span className="filter-pill-count">
              {contracts.filter((c) => c.status === "ingested").length}
            </span>
          </button>
          <button
            className={`filter-pill ${filterStatus === "pending" ? "active" : ""}`}
            onClick={() => setFilterStatus("pending")}
          >
            Pending{" "}
            <span className="filter-pill-count">
              {contracts.filter((c) => c.status === "pending").length}
            </span>
          </button>
          {failedCount > 0 && (
            <button
              className={`filter-pill ${filterStatus === "failed" ? "active" : ""}`}
              onClick={() => setFilterStatus("failed")}
            >
              Failed <span className="filter-pill-count">{failedCount}</span>
            </button>
          )}
        </div>

        {/* Sort & View Mode Switcher */}
        <div className="vault-actions-group">
          <div className="sort-select-wrapper">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              title="Sort contracts list"
            >
              <option value="newest">Sort: Newest First</option>
              <option value="oldest">Sort: Oldest First</option>
              <option value="name-asc">Sort: Name (A to Z)</option>
              <option value="name-desc">Sort: Name (Z to A)</option>
            </select>
          </div>

          <div className="view-mode-toggle">
            <button
              className={`btn-view-toggle ${viewMode === "grid" ? "active" : ""}`}
              onClick={() => setViewMode("grid")}
              title="Grid View (Cards)"
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
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="14" y="14" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
              </svg>
            </button>
            <button
              className={`btn-view-toggle ${viewMode === "table" ? "active" : ""}`}
              onClick={() => setViewMode("table")}
              title="Table View (List)"
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
                <line x1="8" y1="6" x2="21" y2="6" />
                <line x1="8" y1="12" x2="21" y2="12" />
                <line x1="8" y1="18" x2="21" y2="18" />
                <line x1="3" y1="6" x2="3.01" y2="6" />
                <line x1="3" y1="12" x2="3.01" y2="12" />
                <line x1="3" y1="18" x2="3.01" y2="18" />
              </svg>
            </button>
          </div>
        </div>
      </section>

      {/* ── 4. Main Contract Vault Display ──────────────────────────────────── */}
      {isLoading ? (
        <div className="vault-cards-grid">
          {[1, 2, 3, 4, 5, 6].map((idx) => (
            <div key={idx} className="skeleton-card" />
          ))}
        </div>
      ) : isError ? (
        <div className="vault-empty-state">
          <div className="vault-empty-icon" style={{ color: "var(--color-danger)" }}>
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h3>Failed to Load Contracts</h3>
          <p style={{ color: "var(--color-text-muted)", marginTop: "4px" }}>
            {(error as any)?.message || "Could not retrieve contract data from server."}
          </p>
          <button onClick={() => refetch()} className="btn btn-primary mt-4">
            Try Again
          </button>
        </div>
      ) : processedContracts.length === 0 ? (
        <div className="vault-empty-state">
          <div className="vault-empty-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="32"
              height="32"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
              />
            </svg>
          </div>
          <h3>
            {searchQuery || filterStatus !== "all"
              ? "No matching contracts found"
              : "Your Contract Vault is Empty"}
          </h3>
          <p style={{ color: "var(--color-text-muted)", marginTop: "4px", maxWidth: "420px" }}>
            {searchQuery || filterStatus !== "all"
              ? "Try adjusting your search query or reset the filter status to see other agreements."
              : "Upload your first legal agreement (PDF, photo scan, or Word doc) to begin automated parsing, clause detection, and IRAC risk assessment."}
          </p>
          {searchQuery || filterStatus !== "all" ? (
            <button
              onClick={() => {
                setSearchQuery("");
                setFilterStatus("all");
              }}
              className="btn btn-secondary mt-4"
            >
              Clear Filters
            </button>
          ) : (
            <Link to="/contracts/upload" className="btn btn-primary mt-4">
              Upload First Contract
            </Link>
          )}
        </div>
      ) : viewMode === "grid" ? (
        /* ── Grid View: Cards ────────────────────────────────────────────── */
        <div className="vault-cards-grid">
          {processedContracts.map((contract) => (
            <div key={contract.id} className="contract-vault-card">
              <div>
                <div className="card-top-header">
                  <span className="doc-type-tag">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="12"
                      height="12"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2.5"
                    >
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                    </svg>
                    {getDocTypeIcon(contract.filename)}
                  </span>

                  <span className={`status-badge status-${contract.status}`}>
                    <span className="status-badge-dot" />
                    {contract.status}
                  </span>
                </div>

                <Link
                  to={`/contracts/${contract.id}`}
                  className="card-title-link"
                  title={contract.filename}
                >
                  {contract.filename}
                </Link>

                <div className="card-meta-row">
                  <span>Uploaded {formatDate(contract.created_at)}</span>
                  <span>•</span>
                  <span>ID #{contract.id}</span>
                </div>
              </div>

              <div className="card-actions-footer">
                <div className="card-primary-actions">
                  <button
                    onClick={() => navigate(`/contracts/${contract.id}`)}
                    className="btn btn-secondary btn-sm"
                    title="Open Contract Workspace"
                  >
                    View Analysis
                  </button>
                  <button
                    onClick={() => navigate(`/contracts/${contract.id}/ask`)}
                    className="btn btn-secondary btn-sm"
                    title="Ask Grounded Q&A"
                  >
                    Ask Q&A
                  </button>
                </div>

                <button
                  onClick={() => setContractToDelete(contract)}
                  className="btn btn-icon-sm"
                  style={{ color: "var(--color-danger)" }}
                  title="Delete Contract"
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
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* ── Table View: Rows ────────────────────────────────────────────── */
        <div className="vault-table-panel">
          <table className="vault-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Type</th>
                <th>Upload Date</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {processedContracts.map((contract) => (
                <tr key={contract.id}>
                  <td>
                    <div
                      className="vault-table-title"
                      onClick={() => navigate(`/contracts/${contract.id}`)}
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="var(--color-primary)"
                        strokeWidth="2"
                      >
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <span>{contract.filename}</span>
                    </div>
                  </td>
                  <td>
                    <span className="doc-type-tag" style={{ display: "inline-flex" }}>
                      {getDocTypeIcon(contract.filename)}
                    </span>
                  </td>
                  <td>{formatDate(contract.created_at)}</td>
                  <td>
                    <span className={`status-badge status-${contract.status}`}>
                      <span className="status-badge-dot" />
                      {contract.status}
                    </span>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <div style={{ display: "inline-flex", gap: "8px", alignItems: "center" }}>
                      <button
                        onClick={() => navigate(`/contracts/${contract.id}`)}
                        className="btn btn-secondary btn-sm"
                      >
                        Analysis
                      </button>
                      <button
                        onClick={() => navigate(`/contracts/${contract.id}/ask`)}
                        className="btn btn-secondary btn-sm"
                      >
                        Q&A
                      </button>
                      <button
                        onClick={() => setContractToDelete(contract)}
                        className="btn btn-icon-sm"
                        style={{ color: "var(--color-danger)" }}
                        title="Delete Contract"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <polyline points="3 6 5 6 21 6" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── 5. Delete Confirmation Modal ────────────────────────────────────── */}
      {contractToDelete && (
        <div className="modal-overlay" onClick={() => setContractToDelete(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "14px" }}>
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: "50%",
                  background: "rgba(244, 63, 94, 0.12)",
                  color: "var(--color-danger)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
              </div>
              <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: "700" }}>Delete Contract?</h3>
            </div>

            <p style={{ color: "var(--color-text-muted)", fontSize: "0.9rem", lineHeight: "1.5" }}>
              Are you sure you want to delete <strong>"{contractToDelete.filename}"</strong>? This
              document and its analysis report will be permanently removed from your vault.
            </p>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "24px" }}>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setContractToDelete(null)}
                disabled={deleteMutation.isPending}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => deleteMutation.mutate(contractToDelete.id)}
                disabled={deleteMutation.isPending}
              >
                {deleteMutation.isPending ? <div className="spinner spinner-sm" /> : "Permanently Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
