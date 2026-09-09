import React, { useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuthStore } from "../store/useAuthStore";
import {
  fetchActivityHistory,
  type AuditLogItem,
  type HistoryFilterParams,
} from "../services/historyService";
import { Skeleton } from "../components/Skeleton";
import "./HistoryPage.css";

const PAGE_SIZE = 25;

export const HistoryPage: React.FC = () => {
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();

  // Filter States
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [datePreset, setDatePreset] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedMetadata, setExpandedMetadata] = useState<Record<number, boolean>>({});
  const [page, setPage] = useState<number>(0);

  // Compute ISO date range from preset
  const dateRange = useMemo<{ start?: string; end?: string }>(() => {
    const now = new Date();
    if (datePreset === "TODAY") {
      const start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).toISOString();
      return { start };
    }
    if (datePreset === "7DAYS") {
      const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
      return { start };
    }
    if (datePreset === "30DAYS") {
      const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000).toISOString();
      return { start };
    }
    return {};
  }, [datePreset]);

  // Query Parameters
  const queryParams: HistoryFilterParams = useMemo(
    () => ({
      category: selectedCategory,
      status: selectedStatus,
      start_date: dateRange.start,
      end_date: dateRange.end,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    [selectedCategory, selectedStatus, dateRange, page]
  );

  // TanStack Query for Paginated Activity Feed
  const {
    data: historyData,
    isLoading,
    isFetching,
    refetch,
  } = useQuery({
    queryKey: ["activity-history", user?.id, queryParams],
    queryFn: () => fetchActivityHistory(queryParams),
    enabled: !!user?.id,
    staleTime: 30000,
  });

  const items = historyData?.items || [];
  const total = historyData?.total || 0;
  const totalPages = Math.ceil(total / PAGE_SIZE) || 1;

  // Client-side quick search filtering (description or action)
  const displayedItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    const q = searchQuery.toLowerCase();
    return items.filter(
      (item) =>
        item.description.toLowerCase().includes(q) ||
        item.action.toLowerCase().includes(q) ||
        (item.metadata_json?.filename &&
          String(item.metadata_json.filename).toLowerCase().includes(q))
    );
  }, [items, searchQuery]);

  // Telemetry Aggregates
  const stats = useMemo(() => {
    return {
      total: total,
      auth: items.filter((i) => i.category === "AUTH").length,
      contracts: items.filter((i) => i.category === "CONTRACTS").length,
      analysis: items.filter((i) => i.category === "ANALYSIS").length,
      chat: items.filter((i) => i.category === "CHAT").length,
    };
  }, [items, total]);

  const toggleMetadata = (id: number) => {
    setExpandedMetadata((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  // Export JSON compliance audit log
  const handleExportJSON = () => {
    if (!items.length) return;
    const exportData = {
      user_email: user?.email,
      exported_at: new Date().toISOString(),
      filter_category: selectedCategory,
      filter_status: selectedStatus,
      total_records_in_export: displayedItems.length,
      records: displayedItems,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `audit_trail_${user?.email || "user"}_${new Date()
      .toISOString()
      .slice(0, 10)}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Human-readable date formatter
  const formatTimestamp = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  // Render appropriate node icon based on event category
  const renderCategoryIcon = (category: string) => {
    switch (category) {
      case "AUTH":
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        );
      case "CONTRACTS":
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
        );
      case "ANALYSIS":
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
          </svg>
        );
      case "CHAT":
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        );
      case "SEARCH":
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        );
      case "SECURITY":
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        );
      default:
        return (
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <circle cx="12" cy="12" r="10" />
          </svg>
        );
    }
  };

  return (
    <div className="history-page-container">
      {/* Hero Card */}
      <div className="history-hero-card">
        <div className="history-hero-top">
          <div>
            <div className="history-hero-badge">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              Cryptographic Audit & Compliance Trail
            </div>
            <h1 className="history-hero-title">Activity Timeline & Governance</h1>
            <p className="history-hero-desc">
              Every document ingestion, AI analysis execution, semantic query, and security event is
              permanently logged with client context, execution status, and plain-English summaries.
            </p>
          </div>

          <div className="history-hero-actions">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => navigate("/conversations")}
              title="Open full Q&A conversation threads"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <span>View Q&A Conversations</span>
            </button>

            <button
              className="btn btn-secondary btn-sm"
              onClick={handleExportJSON}
              disabled={isLoading || displayedItems.length === 0}
              title="Download full JSON audit report"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              <span>Export Audit Log</span>
            </button>
          </div>
        </div>

        {/* Telemetry Counters */}
        <div className="history-stats-grid">
          <div className="history-stat-box">
            <span className="history-stat-num">{total}</span>
            <span className="history-stat-label">Total Events Recorded</span>
          </div>
          <div className="history-stat-box">
            <span className="history-stat-num" style={{ color: "#c084fc" }}>
              {stats.auth}
            </span>
            <span className="history-stat-label">Auth & 2FA Sessions</span>
          </div>
          <div className="history-stat-box">
            <span className="history-stat-num" style={{ color: "#60a5fa" }}>
              {stats.contracts}
            </span>
            <span className="history-stat-label">Document Ingestions</span>
          </div>
          <div className="history-stat-box">
            <span className="history-stat-num" style={{ color: "#818cf8" }}>
              {stats.analysis}
            </span>
            <span className="history-stat-label">AI Analyses Run</span>
          </div>
          <div className="history-stat-box">
            <span className="history-stat-num" style={{ color: "#34d399" }}>
              {stats.chat}
            </span>
            <span className="history-stat-label">Grounded Inquiries</span>
          </div>
        </div>
      </div>

      {/* Filter and Control Bar */}
      <div className="history-filter-panel">
        <div className="history-filter-row">
          {/* Quick Search */}
          <div className="history-search-input-wrapper">
            <svg className="history-search-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              className="history-search-input"
              placeholder="Search actions or documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {/* Date Range & Status Selectors */}
          <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
            <select
              className="history-date-select"
              value={datePreset}
              onChange={(e) => {
                setDatePreset(e.target.value);
                setPage(0);
              }}
            >
              <option value="ALL">All Time</option>
              <option value="TODAY">Today Only</option>
              <option value="7DAYS">Past 7 Days</option>
              <option value="30DAYS">Past 30 Days</option>
            </select>

            <select
              className="history-date-select"
              value={selectedStatus}
              onChange={(e) => {
                setSelectedStatus(e.target.value);
                setPage(0);
              }}
            >
              <option value="ALL">All Statuses</option>
              <option value="SUCCESS">Success Only</option>
              <option value="FAILURE">Failures / Alerts</option>
            </select>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => refetch()}
              disabled={isFetching}
              title="Refresh timeline"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                style={{ animation: isFetching ? "spin 1s linear infinite" : "none" }}
              >
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
              </svg>
              <span>{isFetching ? "Syncing..." : "Refresh"}</span>
            </button>
          </div>
        </div>

        {/* Category Filter Pills */}
        <div className="history-pill-group">
          {[
            { id: "ALL", label: "All Events" },
            { id: "AUTH", label: "Auth & Sessions" },
            { id: "CONTRACTS", label: "Documents" },
            { id: "ANALYSIS", label: "AI Intelligence" },
            { id: "CHAT", label: "Q&A Threads" },
            { id: "SEARCH", label: "Semantic Search" },
            { id: "SECURITY", label: "Account & 2FA" },
          ].map((cat) => (
            <button
              key={cat.id}
              className={`history-filter-pill ${selectedCategory === cat.id ? "active" : ""}`}
              onClick={() => {
                setSelectedCategory(cat.id);
                setPage(0);
              }}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Timeline List */}
      <div className="history-feed-panel">
        {isLoading ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px", padding: "20px 0" }}>
            <Skeleton height={80} borderRadius={14} />
            <Skeleton height={80} borderRadius={14} />
            <Skeleton height={80} borderRadius={14} />
            <Skeleton height={80} borderRadius={14} />
          </div>
        ) : displayedItems.length === 0 ? (
          <div className="history-empty-card">
            <div className="history-empty-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h3 className="history-empty-title">No Audit Events Found</h3>
            <p className="history-empty-desc">
              No recorded activity matches your current filters. Try changing your category, status,
              or date range selection.
            </p>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setSelectedCategory("ALL");
                setSelectedStatus("ALL");
                setDatePreset("ALL");
                setSearchQuery("");
                setPage(0);
              }}
            >
              Clear All Filters
            </button>
          </div>
        ) : (
          <div className="history-timeline-wrapper">
            {displayedItems.map((item: AuditLogItem) => {
              const catClass = (item.category || "general").toLowerCase();
              const isMetaExpanded = !!expandedMetadata[item.id];

              return (
                <div key={item.id} className="history-item-card">
                  {/* Timeline Node */}
                  <div className={`history-node-icon node-${catClass}`} title={item.category}>
                    {renderCategoryIcon(item.category)}
                  </div>

                  {/* Card Body */}
                  <div className="history-item-content">
                    <div className="history-item-header">
                      <div className="history-item-title-group">
                        <span className={`history-category-badge badge-${catClass}`}>
                          {item.category}
                        </span>
                        <h4 className="history-item-desc">{item.description}</h4>
                        <span
                          className={`history-status-badge ${
                            item.status === "FAILURE" ? "failure" : "success"
                          }`}
                        >
                          {item.status === "SUCCESS" ? "✓ SUCCESS" : "⚠ FAILURE"}
                        </span>
                      </div>
                      <span className="history-item-time" title={item.timestamp}>
                        {formatTimestamp(item.timestamp)}
                      </span>
                    </div>

                    {/* Meta Context */}
                    <div className="history-item-meta">
                      <span className="history-meta-pill">
                        <span className="history-action-code">{item.action}</span>
                      </span>

                      {item.ip_address && (
                        <span className="history-meta-pill" title="Client IP Address">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <line x1="2" y1="12" x2="22" y2="12" />
                            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                          </svg>
                          {item.ip_address}
                        </span>
                      )}

                      {item.user_agent && (
                        <span className="history-meta-pill" title={item.user_agent}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                            <line x1="8" y1="21" x2="16" y2="21" />
                            <line x1="12" y1="17" x2="12" y2="21" />
                          </svg>
                          {item.user_agent.length > 32
                            ? item.user_agent.slice(0, 30) + "..."
                            : item.user_agent}
                        </span>
                      )}
                    </div>

                    {/* Action Links */}
                    <div className="history-item-actions">
                      {item.resource_id && (item.category === "CONTRACTS" || item.category === "ANALYSIS" || item.category === "CHAT") && (
                        <Link to={`/contracts/${item.resource_id}`} className="history-link-btn">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                            <polyline points="15 3 21 3 21 9" />
                            <line x1="10" y1="14" x2="21" y2="3" />
                          </svg>
                          View Document
                        </Link>
                      )}

                      {item.action === "SEARCH_PERFORMED" && item.metadata_json?.query && (
                        <Link to={`/search?q=${encodeURIComponent(item.metadata_json.query)}`} className="history-link-btn">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="11" cy="11" r="8" />
                            <line x1="21" y1="21" x2="16.65" y2="16.65" />
                          </svg>
                          Repeat Search
                        </Link>
                      )}

                      {item.action === "QA_MESSAGE_SENT" && item.metadata_json?.conversation_id && item.resource_id && (
                        <Link
                          to={`/contracts/${item.resource_id}/ask?conversation_id=${item.metadata_json.conversation_id}`}
                          className="history-link-btn"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                          </svg>
                          Open Discussion
                        </Link>
                      )}

                      {item.metadata_json && Object.keys(item.metadata_json).length > 0 && (
                        <button
                          className="history-inspect-btn"
                          onClick={() => toggleMetadata(item.id)}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points={isMetaExpanded ? "18 15 12 9 6 15" : "6 9 12 15 18 9"} />
                          </svg>
                          {isMetaExpanded ? "Hide Metadata" : "View Metadata"}
                        </button>
                      )}
                    </div>

                    {/* Metadata JSON Box */}
                    {isMetaExpanded && item.metadata_json && (
                      <pre className="history-metadata-box">
                        {JSON.stringify(item.metadata_json, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination Bar */}
        {total > PAGE_SIZE && (
          <div className="history-pagination-bar">
            <span className="history-page-info">
              Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total} events
            </span>
            <div className="history-page-controls">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0 || isLoading}
              >
                ← Previous
              </button>
              <span style={{ fontSize: "0.85rem", color: "var(--color-text-main)", fontWeight: "600" }}>
                Page {page + 1} of {totalPages}
              </span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1 || isLoading}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default HistoryPage;
