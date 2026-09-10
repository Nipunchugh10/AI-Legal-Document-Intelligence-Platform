import { Component, type ErrorInfo, type ReactNode } from "react";
import "./ErrorScreen.css";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  showDetail: boolean;
}

/**
 * Top-level React error boundary.
 *
 * It renders ABOVE the router, so it navigates via window.location instead of
 * useNavigate. Crucially, recovering from a render error NEVER clears the auth
 * tokens — a UI crash must not end the user's session. The user can retry
 * in place, return to the dashboard, or reload, and remain logged in.
 */
export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    showDetail: false,
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // eslint-disable-next-line no-console
    console.error("Uncaught React error:", error, errorInfo);
  }

  private handleTryAgain = () => {
    // Reset the boundary and re-render the tree — session stays intact.
    this.setState({ hasError: false, error: null, showDetail: false });
  };

  private handleDashboard = () => {
    window.location.assign("/dashboard");
  };

  private handleReload = () => {
    window.location.reload();
  };

  public render() {
    if (!this.state.hasError) return this.props.children;

    const { error, showDetail } = this.state;

    return (
      <div className="error-screen error-screen--full error-screen--server" role="alert">
        <div className="error-screen__card">
          <div className="error-screen__icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <h1 className="error-screen__title">Something Went Wrong</h1>
          <p className="error-screen__message">
            The interface hit an unexpected error. Your session is still active — try again,
            or head back to your dashboard.
          </p>

          <div className="error-screen__actions">
            <button type="button" className="error-screen__btn error-screen__btn--primary" onClick={this.handleTryAgain}>
              Try Again
            </button>
            <button type="button" className="error-screen__btn error-screen__btn--secondary" onClick={this.handleDashboard}>
              Back to Dashboard
            </button>
            <button type="button" className="error-screen__btn error-screen__btn--secondary" onClick={this.handleReload}>
              Reload
            </button>
          </div>

          {error && (
            <div className="error-screen__detail-wrap">
              <button
                type="button"
                className="error-screen__detail-toggle"
                aria-expanded={showDetail}
                onClick={() => this.setState((s) => ({ showDetail: !s.showDetail }))}
              >
                {showDetail ? "Hide technical details" : "Show technical details"}
              </button>
              {showDetail && <pre className="error-screen__detail">{error.toString()}</pre>}
            </div>
          )}
        </div>
      </div>
    );
  }
}
