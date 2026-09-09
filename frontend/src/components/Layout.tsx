import React, { useState, useEffect } from "react";
import { Outlet, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/useAuthStore";
import { useContractStore } from "../store/useContractStore";
import { IdleTimer } from "./IdleTimer";
import { CommandPalette } from "./CommandPalette";
import "./Layout.css";

interface LayoutProps {
  children?: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const searchQuery = useContractStore((state) => state.searchQuery);
  const setSearchQuery = useContractStore((state) => state.setSearchQuery);

  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isPaletteOpen, setIsPaletteOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return (localStorage.getItem("theme") as "dark" | "light") || "dark";
  });

  // Synchronize theme changes
  useEffect(() => {
    localStorage.setItem("theme", theme);
    if (theme === "light") {
      document.documentElement.classList.add("light-theme");
    } else {
      document.documentElement.classList.remove("light-theme");
    }
  }, [theme]);

  // Global Ctrl+K / Cmd+K Command Palette hotkey
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Close mobile drawer on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  // Compute breadcrumb title based on active pathname
  const getBreadcrumb = () => {
    const path = location.pathname;
    if (path.startsWith("/dashboard")) return "Contract Vault";
    if (path.startsWith("/search")) return "Semantic Search";
    if (path.startsWith("/contracts/upload")) return "Upload Document";
    if (path.startsWith("/contracts/compare")) return "Version Comparison";
    if (path.includes("/ask")) return "Grounded Q&A";
    if (path.startsWith("/contracts/")) return "Contract Intelligence";
    if (path.startsWith("/security")) return "Security & 2FA";
    if (path.startsWith("/history")) return "Activity History";
    if (path.startsWith("/conversations")) return "Q&A Conversations";
    return "Workspace";
  };

  const userInitial = user?.email ? user.email.charAt(0).toUpperCase() : "U";

  return (
    <div className="app-shell">
      {/* 15-minute Inactivity Auto-Logout Tracker with 13-min Warning */}
      <IdleTimer />

      {/* Global Command Palette (Cmd+K / Ctrl+K) */}
      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setIsPaletteOpen(false)}
        onToggleTheme={toggleTheme}
        isDarkTheme={theme === "dark"}
      />

      {/* Mobile Navigation Drawer Backdrop */}
      {isMobileMenuOpen && (
        <div
          className="mobile-drawer-backdrop"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* --- Sidebar Navigation (Desktop & Mobile Drawer) --- */}
      <aside
        className={`sidebar ${isCollapsed ? "collapsed" : ""} ${
          isMobileMenuOpen ? "mobile-open" : ""
        }`}
      >
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <div className="sidebar-brand" onClick={() => navigate("/dashboard")}>
            <div className="brand-icon-wrapper">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
                <path d="M7 21h10" />
                <path d="M12 3v18" />
                <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" />
              </svg>
            </div>
            {!isCollapsed && (
              <span className="brand-title">
                Legal<span>Intel</span>
              </span>
            )}
          </div>
          <button
            className="btn-sidebar-toggle"
            onClick={() => setIsCollapsed(!isCollapsed)}
            title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            aria-label="Toggle Sidebar"
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
              {isCollapsed ? (
                <polyline points="13 17 18 12 13 7" />
              ) : (
                <polyline points="11 17 6 12 11 7" />
              )}
            </svg>
          </button>
        </div>

        {/* Sidebar Navigation Items */}
        <nav className="sidebar-nav">
          <div className="nav-section-title">Core Workspace</div>

          <NavLink
            to="/dashboard"
            className={({ isActive }) => `nav-link-item ${isActive ? "active" : ""}`}
            title="Contract Vault"
          >
            <div className="nav-link-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />
              </svg>
            </div>
            <span className="nav-link-text">Contract Vault</span>
          </NavLink>

          <NavLink
            to="/search"
            className={({ isActive }) => `nav-link-item ${isActive ? "active" : ""}`}
            title="Semantic Search"
          >
            <div className="nav-link-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            <span className="nav-link-text">Semantic Search</span>
          </NavLink>

          <NavLink
            to="/contracts/upload"
            className={({ isActive }) => `nav-link-item ${isActive ? "active" : ""}`}
            title="Upload Document"
          >
            <div className="nav-link-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <span className="nav-link-text">Upload Document</span>
          </NavLink>

          <NavLink
            to="/contracts/compare"
            className={({ isActive }) => `nav-link-item ${isActive ? "active" : ""}`}
            title="Compare Contracts"
          >
            <div className="nav-link-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
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
            </div>
            <span className="nav-link-text">Compare Versions</span>
          </NavLink>

          <div className="nav-section-title">Audit & Account</div>

          <NavLink
            to="/history"
            className={({ isActive }) => `nav-link-item ${isActive ? "active" : ""}`}
            title="Activity History"
          >
            <div className="nav-link-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
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
            <span className="nav-link-text">Activity History</span>
          </NavLink>

          <NavLink
            to="/conversations"
            className={({ isActive }) => `nav-link-item ${isActive ? "active" : ""}`}
            title="Q&A Conversations"
          >
            <div className="nav-link-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <span className="nav-link-text">Q&A Conversations</span>
          </NavLink>

          <NavLink
            to="/security"
            className={({ isActive }) => `nav-link-item ${isActive ? "active" : ""}`}
            title="Security & 2FA"
          >
            <div className="nav-link-icon">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <span className="nav-link-text">Security & 2FA</span>
          </NavLink>
        </nav>

        {/* Sidebar Footer / User Profile */}
        <div className="sidebar-footer">
          <div className="user-profile-summary">
            <div className="user-avatar-circle" title={user?.email || "User"}>
              {userInitial}
            </div>
            {!isCollapsed && (
              <div className="user-text-info">
                <span className="user-email-display" title={user?.email}>
                  {user?.email || "Signed In"}
                </span>
                <span className="user-role-badge">
                  {user?.is_2fa_enabled ? "🛡️ 2FA Verified" : "Standard Account"}
                </span>
              </div>
            )}
            <button
              className="btn-logout-sidebar"
              onClick={handleLogout}
              title="Sign Out"
              aria-label="Sign Out"
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
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* --- Main Content Area --- */}
      <div className="main-layout-wrapper">
        {/* Top Header Bar */}
        <header className="top-header">
          <div className="top-header-left">
            {/* Mobile Drawer Hamburger Button */}
            <button
              className="btn-mobile-menu-toggle"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label="Open Navigation Menu"
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
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>

            <div className="breadcrumb-trail">
              <span>Workspace</span>
              <span>/</span>
              <span className="breadcrumb-active">{getBreadcrumb()}</span>
            </div>

            {/* Quick Search & Command Palette Trigger */}
            <div
              className="header-search-bar"
              onClick={() => setIsPaletteOpen(true)}
              title="Click or press Ctrl+K to open Command Palette"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                type="text"
                placeholder="Search contracts or press ⌘K..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                readOnly
              />
              <span className="search-kbd-pill">⌘K</span>
            </div>
          </div>

          <div className="top-header-right">
            {/* Session Security Indicator */}
            <div className="session-security-pill" title="Encrypted Session Active">
              <div className="security-dot-pulse" />
              <span>Protected Session</span>
            </div>

            {/* Theme Switcher Button */}
            <button
              className="btn-icon-header"
              onClick={toggleTheme}
              title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
              aria-label="Toggle Theme"
            >
              {theme === "dark" ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <circle cx="12" cy="12" r="5" />
                  <line x1="12" y1="1" x2="12" y2="3" />
                  <line x1="12" y1="21" x2="12" y2="23" />
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                  <line x1="1" y1="12" x2="3" y2="12" />
                  <line x1="21" y1="12" x2="23" y2="12" />
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>

            {/* Quick Upload CTA */}
            <button
              className="btn btn-primary btn-header-upload"
              onClick={() => navigate("/contracts/upload")}
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
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              <span>Upload Contract</span>
            </button>
          </div>
        </header>

        {/* Dynamic Page Viewport */}
        <main className="page-viewport">
          {children || <Outlet />}
        </main>
      </div>

      {/* --- Mobile Bottom Navigation Bar (< 768px) --- */}
      <nav className="mobile-bottom-nav">
        <NavLink to="/dashboard" className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />
          </svg>
          <span>Vault</span>
        </NavLink>
        <NavLink to="/contracts/upload" className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <span>Upload</span>
        </NavLink>
        <NavLink to="/contracts/compare" className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M16 3h5v5" />
            <path d="M8 3H3v5" />
            <path d="M12 21V9" />
          </svg>
          <span>Compare</span>
        </NavLink>
        <NavLink to="/security" className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}>
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          <span>Security</span>
        </NavLink>
      </nav>
    </div>
  );
};
