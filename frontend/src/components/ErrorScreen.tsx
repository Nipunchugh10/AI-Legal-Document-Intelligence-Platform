import React from "react";
import { useNavigate } from "react-router-dom";
import type { ErrorKind } from "../services/errorUtils";
import "./ErrorScreen.css";

export interface ErrorScreenAction {
  label: string;
  onClick: () => void;
  variant?: "primary" | "secondary";
}

interface ErrorScreenProps {
  /** Big status code, e.g. "404", "403", "500", or "!". */
  code?: string;
  kind?: ErrorKind;
  title: string;
  message: string;
  /** Optional technical detail (collapsed by default). */
  detail?: string;
  actions?: ErrorScreenAction[];
  /**
   * "page" (default) fills the content area inside the app Layout;
   * "full" is a standalone full-viewport screen (ErrorBoundary, pre-auth).
   */
  variant?: "page" | "full";
}

const ICONS: Record<ErrorKind, React.ReactNode> = {
  notfound: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="7" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
      <line x1="8" y1="11" x2="14" y2="11" />
    </svg>
  ),
  forbidden: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="11" width="16" height="10" rx="2" />
      <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      <line x1="12" y1="15" x2="12" y2="17" />
    </svg>
  ),
  server: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
  network: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1 1l22 22" />
      <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55" />
      <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39" />
      <path d="M10.71 5.05A16 16 0 0 1 22.58 9" />
      <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88" />
      <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
      <line x1="12" y1="20" x2="12.01" y2="20" />
    </svg>
  ),
  unknown: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  ),
};

/**
 * Polished, theme-aware error screen used everywhere a request fails or a
 * route is unknown. It never mutates auth state — recovering from an error
 * keeps the user's session fully intact.
 */
export const ErrorScreen: React.FC<ErrorScreenProps> = ({
  code,
  kind = "unknown",
  title,
  message,
  detail,
  actions,
  variant = "page",
}) => {
  const navigate = useNavigate();
  const [showDetail, setShowDetail] = React.useState(false);

  const resolvedActions: ErrorScreenAction[] =
    actions && actions.length > 0
      ? actions
      : [{ label: "Back to Dashboard", onClick: () => navigate("/dashboard"), variant: "primary" }];

  return (
    <div className={`error-screen error-screen--${variant} error-screen--${kind}`} role="alert">
      <div className="error-screen__card">
        {code && <div className="error-screen__code">{code}</div>}
        <div className="error-screen__icon">{ICONS[kind]}</div>
        <h1 className="error-screen__title">{title}</h1>
        <p className="error-screen__message">{message}</p>

        <div className="error-screen__actions">
          {resolvedActions.map((a, i) => (
            <button
              key={i}
              type="button"
              className={`error-screen__btn error-screen__btn--${a.variant ?? "secondary"}`}
              onClick={a.onClick}
            >
              {a.label}
            </button>
          ))}
        </div>

        {detail && (
          <div className="error-screen__detail-wrap">
            <button
              type="button"
              className="error-screen__detail-toggle"
              onClick={() => setShowDetail((v) => !v)}
              aria-expanded={showDetail}
            >
              {showDetail ? "Hide technical details" : "Show technical details"}
            </button>
            {showDetail && <pre className="error-screen__detail">{detail}</pre>}
          </div>
        )}
      </div>
    </div>
  );
};

export default ErrorScreen;
