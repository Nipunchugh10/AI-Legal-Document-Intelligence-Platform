import React, { useState, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { useAuthStore } from "../store/useAuthStore";
import "./CommandPalette.css";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onToggleTheme: () => void;
  isDarkTheme: boolean;
}

interface ContractItem {
  id: number;
  filename: string;
  status: string;
}

interface PaletteAction {
  id: string;
  title: string;
  category: "Navigation" | "Contract" | "Action";
  icon: string;
  subtext?: string;
  onSelect: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onToggleTheme,
  isDarkTheme,
}) => {
  const navigate = useNavigate();
  const logout = useAuthStore((state) => state.logout);
  const [query, setQuery] = useState("");
  const [contracts, setContracts] = useState<ContractItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);

      // Fetch user contracts for quick jumping
      api
        .get<ContractItem[]>("/contracts/")
        .then((res) => setContracts(res.data))
        .catch(() => setContracts([]));
    }
  }, [isOpen]);

  const baseActions: PaletteAction[] = useMemo(
    () => [
      {
        id: "nav-dashboard",
        title: "Go to Contract Vault",
        category: "Navigation",
        icon: "📁",
        subtext: "View all your stored legal documents",
        onSelect: () => {
          navigate("/dashboard");
          onClose();
        },
      },
      {
        id: "nav-upload",
        title: "Upload New Document",
        category: "Navigation",
        icon: "📤",
        subtext: "Ingest PDF, DOCX, scans, or text documents",
        onSelect: () => {
          navigate("/contracts/upload");
          onClose();
        },
      },
      {
        id: "nav-search",
        title: "Semantic Contract Search",
        category: "Navigation",
        icon: "🔍",
        subtext: "Search clauses and fine print with vector AI",
        onSelect: () => {
          navigate("/search");
          onClose();
        },
      },
      {
        id: "nav-compare",
        title: "Compare Contract Versions",
        category: "Navigation",
        icon: "⚖️",
        subtext: "Side-by-side visual diff and clause delta",
        onSelect: () => {
          navigate("/contracts/compare");
          onClose();
        },
      },
      {
        id: "nav-history",
        title: "View Activity History",
        category: "Navigation",
        icon: "📜",
        subtext: "Full timeline of audit events and session logs",
        onSelect: () => {
          navigate("/history");
          onClose();
        },
      },
      {
        id: "nav-conversations",
        title: "Q&A Conversations",
        category: "Navigation",
        icon: "💬",
        subtext: "Explore and resume past grounded contract discussions",
        onSelect: () => {
          navigate("/conversations");
          onClose();
        },
      },
      {
        id: "nav-security",
        title: "Security & 2FA Settings",
        category: "Navigation",
        icon: "🛡️",
        subtext: "Manage Email Two-Factor Authentication and sessions",
        onSelect: () => {
          navigate("/security");
          onClose();
        },
      },
      {
        id: "act-theme",
        title: isDarkTheme ? "Switch to Light Theme" : "Switch to Dark Theme",
        category: "Action",
        icon: isDarkTheme ? "☀️" : "🌙",
        subtext: "Toggle application visual appearance",
        onSelect: () => {
          onToggleTheme();
          onClose();
        },
      },
      {
        id: "act-logout",
        title: "Sign Out",
        category: "Action",
        icon: "🚪",
        subtext: "End your current secure session",
        onSelect: async () => {
          await logout();
          navigate("/login");
          onClose();
        },
      },
    ],
    [navigate, onClose, onToggleTheme, isDarkTheme, logout]
  );

  // Combine static actions with live contracts
  const allItems = useMemo(() => {
    const contractActions: PaletteAction[] = contracts.map((c) => ({
      id: `contract-${c.id}`,
      title: c.filename,
      category: "Contract",
      icon: "📄",
      subtext: `ID #${c.id} • Status: ${c.status}`,
      onSelect: () => {
        navigate(`/contracts/${c.id}`);
        onClose();
      },
    }));

    const combined = [...baseActions, ...contractActions];

    if (!query.trim()) return combined;

    const q = query.toLowerCase();
    return combined.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        (item.subtext && item.subtext.toLowerCase().includes(q))
    );
  }, [baseActions, contracts, query, navigate, onClose]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev < allItems.length - 1 ? prev + 1 : 0));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : allItems.length - 1));
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (allItems[selectedIndex]) {
          allItems[selectedIndex].onSelect();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, allItems, selectedIndex, onClose]);

  if (!isOpen) return null;

  return (
    <div className="palette-backdrop-overlay" onClick={onClose}>
      <div
        className="palette-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* Search Input Bar */}
        <div className="palette-search-header">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            className="palette-input"
            placeholder="Type a command or search contracts..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
          />
          <span className="palette-esc-badge">ESC</span>
        </div>

        {/* Action Items List */}
        <div className="palette-results-list">
          {allItems.length > 0 ? (
            allItems.map((item, idx) => (
              <div
                key={item.id}
                className={`palette-item-row ${idx === selectedIndex ? "selected" : ""}`}
                onClick={item.onSelect}
                onMouseEnter={() => setSelectedIndex(idx)}
              >
                <div className="palette-item-icon">{item.icon}</div>
                <div className="palette-item-info">
                  <div className="palette-item-title">{item.title}</div>
                  {item.subtext && (
                    <div className="palette-item-subtext">{item.subtext}</div>
                  )}
                </div>
                <span className="palette-category-badge">{item.category}</span>
              </div>
            ))
          ) : (
            <div className="palette-empty-results">
              <p>No matching commands or documents found for "{query}"</p>
            </div>
          )}
        </div>

        {/* Footer Shortcut Hints */}
        <div className="palette-footer-hints">
          <div className="hint-item">
            <span className="hint-key">↑</span>
            <span className="hint-key">↓</span>
            <span>Navigate</span>
          </div>
          <div className="hint-item">
            <span className="hint-key">↵</span>
            <span>Select</span>
          </div>
          <div className="hint-item">
            <span className="hint-key">ESC</span>
            <span>Close</span>
          </div>
        </div>
      </div>
    </div>
  );
};
