import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/useAuthStore";
import "./Welcome.css";

export const Welcome: React.FC = () => {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return (localStorage.getItem("theme") as "dark" | "light") || "dark";
  });

  // Apply theme class to document element on mount and state change
  useEffect(() => {
    if (theme === "light") {
      document.documentElement.classList.add("light-theme");
    } else {
      document.documentElement.classList.remove("light-theme");
    }
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  return (
    <div className="welcome-container">
      {/* Navbar section */}
      <header className="welcome-navbar">
        <div
          onClick={() => navigate(isAuthenticated ? "/dashboard" : "/")}
          className="welcome-brand"
          style={{ cursor: "pointer" }}
        >
          Legal<span>Intelligence</span>
        </div>
        <div className="welcome-nav-actions">
          {/* Theme switcher */}
          <button
            onClick={toggleTheme}
            className="theme-toggle-btn"
            title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
            aria-label="Toggle light and dark themes"
          >
            {theme === "dark" ? (
              // Sun Icon
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2m0 14v2m9-9h-2M5 12H3m15.364-6.364l-1.414 1.414M7.05 16.95l-1.414 1.414M16.95 16.95l1.414 1.414M7.05 7.05L5.636 5.636M12 8a4 4 0 100 8 4 4 0 000-8z" />
              </svg>
            ) : (
              // Moon Icon
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
              </svg>
            )}
          </button>

          <Link to="/login" className="welcome-btn-secondary" style={{ padding: "10px 20px", fontSize: "0.95rem" }}>
            Sign In
          </Link>
          <Link to="/register" className="welcome-btn-primary" style={{ padding: "10px 20px", fontSize: "0.95rem" }}>
            Join Now
          </Link>
        </div>
      </header>

      {/* Main hero section */}
      <main className="welcome-hero">
        <div className="welcome-hero-left">
          <h1 className="welcome-headline">
            Understand any contract in <span>seconds</span>.
          </h1>
          <p className="welcome-subhead">
            LegalIntelligence reads the fine print. Detect unfavorable clauses, identify liabilities, and review compliance norms in plain English — instantly.
          </p>

          <div className="welcome-cta-group">
            <Link to="/register" className="welcome-btn-primary">
              Get Started for Free
              <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
              </svg>
            </Link>
            <Link to="/login" className="welcome-btn-secondary">
              Sign In to Workspace
            </Link>
          </div>

          {/* Quick value props list */}
          <div className="welcome-features">
            <div className="welcome-feature-card">
              <span className="welcome-feature-icon" role="img" aria-label="Risk Audit">🔍</span>
              <h3 className="welcome-feature-title">AI Risk Auditing</h3>
              <p className="welcome-feature-desc">
                Automatically locate one-sided liabilities, hidden terms, and unfavorable language.
              </p>
            </div>
            <div className="welcome-feature-card">
              <span className="welcome-feature-icon" role="img" aria-label="Security">🛡️</span>
              <h3 className="welcome-feature-title">Hardened Safety</h3>
              <p className="welcome-feature-desc">
                Protected by bank-grade email 2FA verification and automatic idle timeout enforcement.
              </p>
            </div>
            <div className="welcome-feature-card">
              <span className="welcome-feature-icon" role="img" aria-label="Interactive Q&A">💬</span>
              <h3 className="welcome-feature-title">Plain-English Q&A</h3>
              <p className="welcome-feature-desc">
                Ask specific questions about clauses and get immediate answers with references.
              </p>
            </div>
          </div>
        </div>

        <div className="welcome-hero-right">
          <div className="welcome-hero-glow"></div>
          <div className="welcome-hero-image-wrapper">
            <img
              src="/welcome_hero.jpg"
              alt="AI Document Intelligence Illustration"
              className="welcome-hero-image"
            />
          </div>
        </div>
      </main>
    </div>
  );
};
