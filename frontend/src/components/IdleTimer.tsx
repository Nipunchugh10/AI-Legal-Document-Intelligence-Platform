import React, { useState, useEffect, useRef } from "react";
import { useAuthStore } from "../store/useAuthStore";

export const IdleTimer: React.FC = () => {
  const logout = useAuthStore((state) => state.logout);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const [showWarning, setShowWarning] = useState(false);
  const [countdown, setCountdown] = useState(120); // 2 minutes in seconds

  const lastActiveRef = useRef<number>(Date.now());
  const checkIntervalRef = useRef<number | null>(null);

  const WARNING_LIMIT = 38 * 60 * 1000; // 38 minutes in ms
  const LOGOUT_LIMIT = 40 * 60 * 1000; // 40 minutes in ms

  const resetTimer = () => {
    lastActiveRef.current = Date.now();
    if (showWarning) {
      setShowWarning(false);
      setCountdown(120);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) {
      if (checkIntervalRef.current !== null) {
        clearInterval(checkIntervalRef.current);
        checkIntervalRef.current = null;
      }
      return;
    }

    // Event listeners to track user activity
    const events = ["mousemove", "mousedown", "keypress", "scroll", "click", "touchstart"];
    const handleActivity = () => resetTimer();

    events.forEach((event) => {
      window.addEventListener(event, handleActivity);
    });

    // Check inactivity state every second
    checkIntervalRef.current = window.setInterval(() => {
      const elapsed = Date.now() - lastActiveRef.current;

      if (elapsed >= LOGOUT_LIMIT) {
        // Log out immediately client-side
        logout();
        window.location.href = "/login?expired=true";
      } else if (elapsed >= WARNING_LIMIT) {
        // Show warning modal and compute remaining seconds
        setShowWarning(true);
        const remainingSeconds = Math.max(0, Math.ceil((LOGOUT_LIMIT - elapsed) / 1000));
        setCountdown(remainingSeconds);
      } else {
        if (showWarning) {
          setShowWarning(false);
        }
      }
    }, 1000);

    return () => {
      events.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      if (checkIntervalRef.current !== null) {
        clearInterval(checkIntervalRef.current);
        checkIntervalRef.current = null;
      }
    };
  }, [isAuthenticated, logout, showWarning]);

  if (!showWarning) return null;

  return (
    <div className="modal-backdrop">
      <div className="glass-panel modal-content idle-warning-modal">
        <div className="modal-header">
          <div className="alert-icon-wrapper">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--color-warning)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <h3 className="modal-title">Session Expiring</h3>
        </div>
        <p className="modal-body">
          You have been idle for a while. To protect your legal documents, you will be logged out in{" "}
          <span className="countdown-timer">
            {Math.floor(countdown / 60)}:{(countdown % 60).toString().padStart(2, "0")}
          </span>.
        </p>
        <div className="modal-actions">
          <button className="btn btn-primary" onClick={resetTimer}>
            Stay Logged In
          </button>
        </div>
      </div>
    </div>
  );
};
