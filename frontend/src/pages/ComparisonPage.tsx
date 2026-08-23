import React, { useState, useEffect } from "react";
import api from "../services/api";
import type { Contract } from "../store/useContractStore";

export const ComparisonPage: React.FC = () => {
  const [contracts, setContracts] = useState<Contract[]>([]);
  const [baseId, setBaseId] = useState<number | "">("");
  const [targetId, setTargetId] = useState<number | "">("");
  const [isLoading] = useState(false);

  useEffect(() => {
    api.get<Contract[]>("/contracts/").then((res) => setContracts(res.data)).catch(console.error);
  }, []);

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
        <h1 className="placeholder-title">Side-by-Side Contract Comparison</h1>
        <p className="placeholder-desc">
          Compare revisions, counter-drafts, or historical versions of contracts. Detect modified
          covenants, added liabilities, removed indemnities, and track exposure changes.
        </p>

        {/* Contract Selector Controls */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr auto",
            gap: "16px",
            alignItems: "end",
            marginTop: "12px",
          }}
        >
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Base Contract (Original / V1)</label>
            <select
              className="form-control"
              value={baseId}
              onChange={(e) => setBaseId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Select original contract...</option>
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.filename} ({new Date(c.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Comparison Contract (Revision / V2)</label>
            <select
              className="form-control"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">Select counter-party revision...</option>
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.filename} ({new Date(c.created_at).toLocaleDateString()})
                </option>
              ))}
            </select>
          </div>

          <button
            className="btn btn-primary"
            disabled={!baseId || !targetId || baseId === targetId || isLoading}
            style={{ height: "46px" }}
          >
            Compare Versions
          </button>
        </div>
      </div>

      {/* Feature capabilities grid */}
      <div className="placeholder-grid-features">
        <div className="feature-stub-card">
          <div className="feature-icon-box">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </div>
          <h3 className="feature-card-title">Clause-Level Difference Detection</h3>
          <p className="feature-card-desc">
            Identifies missing clauses, newly inserted warranties, and amended obligations between draft agreements.
          </p>
        </div>

        <div className="feature-stub-card">
          <div className="feature-icon-box">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
          </div>
          <h3 className="feature-card-title">Risk Profile Delta Analysis</h3>
          <p className="feature-card-desc">
            Highlights whether a redlined revision increased or decreased critical exposure for your organization.
          </p>
        </div>

        <div className="feature-stub-card">
          <div className="feature-icon-box">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
            </svg>
          </div>
          <h3 className="feature-card-title">Side-by-Side Track Changes</h3>
          <p className="feature-card-desc">
            Synchronized dual-pane scrolling with green highlights for additions and red highlights for deletions.
          </p>
        </div>
      </div>
    </div>
  );
};
