import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { useAuthStore } from "../store/useAuthStore";

export const Security: React.FC = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 2FA Setup State
  const [step, setStep] = useState<"status" | "verify">("status");
  const [otpDigits, setOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [otpExpirySeconds, setOtpExpirySeconds] = useState(300); // 5 minutes
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Active Sessions State
  interface DeviceSession {
    id: number;
    device_info: string | null;
    ip_address: string | null;
    created_at: string;
    last_active_at: string;
    is_current: boolean;
  }
  const [sessions, setSessions] = useState<DeviceSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);

  const fetchSessions = async () => {
    setIsLoadingSessions(true);
    try {
      const res = await api.get<DeviceSession[]>("/auth/sessions");
      setSessions(res.data);
    } catch (err) {
      console.error("Failed to load active sessions", err);
    } finally {
      setIsLoadingSessions(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleRevokeSession = async (sessionId: number, isCurrent: boolean) => {
    if (isCurrent) {
      if (!window.confirm("Logging out of your current session will log you out of the application. Proceed?")) {
        return;
      }
    } else {
      if (!window.confirm("Are you sure you want to terminate this session?")) {
        return;
      }
    }

    try {
      await api.delete(`/auth/sessions/${sessionId}`);
      if (isCurrent) {
        const logout = useAuthStore.getState().logout;
        await logout();
        navigate("/login?expired=true");
      } else {
        setSuccessMsg("Device session successfully terminated.");
        fetchSessions();
      }
    } catch (err: any) {
      setErrorMsg("Failed to revoke session.");
    }
  };

  const handleRevokeOthers = async () => {
    if (!window.confirm("Are you sure you want to log out of all other devices?")) {
      return;
    }

    try {
      await api.delete("/auth/sessions");
      setSuccessMsg("Logged out of all other devices successfully.");
      fetchSessions();
    } catch (err) {
      setErrorMsg("Failed to revoke other sessions.");
    }
  };

  // Reset digits when transition to verify
  useEffect(() => {
    if (step === "verify") {
      setOtpDigits(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    }
  }, [step]);

  // OTP Countdown timer
  useEffect(() => {
    if (step !== "verify" || otpExpirySeconds <= 0) return;
    const timer = setTimeout(() => {
      setOtpExpirySeconds((prev) => prev - 1);
    }, 1000);
    return () => clearTimeout(timer);
  }, [step, otpExpirySeconds]);



  const handleEnable2FA = async () => {
    setIsSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await api.post("/auth/2fa/enable");
      setOtpExpirySeconds(300); // 5 minutes
      setStep("verify");
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Failed to initiate 2FA. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDisable2FA = async () => {
    if (!window.confirm("Are you sure you want to disable Two-Factor Authentication? Your account will be less secure.")) {
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await api.post("/auth/2fa/disable");
      if (user) {
        setUser({
          ...user,
          is_2fa_enabled: false,
        });
      }
      setSuccessMsg("Two-Factor Authentication has been successfully disabled.");
      setStep("status");
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Failed to disable 2FA. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const newDigits = [...otpDigits];

    if (value.length > 1) {
      const digits = value.slice(0, 6 - index).split("");
      for (let i = 0; i < digits.length; i++) {
        newDigits[index + i] = digits[i];
      }
      setOtpDigits(newDigits);
      const nextIndex = Math.min(index + digits.length, 5);
      inputRefs.current[nextIndex]?.focus();
    } else {
      newDigits[index] = value;
      setOtpDigits(newDigits);
      if (value && index < 5) {
        inputRefs.current[index + 1]?.focus();
      }
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const verifyOtpCode = async (codeOverride?: string) => {
    const code = codeOverride || otpDigits.join("");
    if (code.length !== 6) {
      setErrorMsg("Please enter all 6 digits of the verification code.");
      return;
    }

    if (otpExpirySeconds <= 0) {
      setErrorMsg("OTP has expired. Please request a new code.");
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      await api.post("/auth/2fa/confirm", {
        otp_code: code,
      });

      // Update local user details in store
      if (user) {
        setUser({
          ...user,
          is_2fa_enabled: true,
        });
      }

      setSuccessMsg("Two-Factor Authentication is now active. You'll receive a code by email each time you log in.");
      setStep("status");
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("OTP verification failed. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatExpiryTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const maskEmail = (email: string | undefined | null) => {
    if (!email) return "";
    const parts = email.split("@");
    if (parts.length !== 2) return email;
    const [name, domain] = parts;
    if (name.length <= 2) return `${name[0]}••••@${domain}`;
    return `${name[0]}••••${name[name.length - 1]}@${domain}`;
  };

  return (
    <div className="app-container">
      {/* Navbar Component */}
      <header className="navbar">
        <div
          onClick={() => navigate(user ? "/dashboard" : "/")}
          className="navbar-brand"
          style={{ cursor: "pointer" }}
        >
          Legal<span>Intelligence</span>
        </div>
        <div className="navbar-actions">
          <span className="user-email">{user?.email}</span>
          <button onClick={() => navigate("/dashboard")} className="btn btn-secondary btn-nav-action">
            Workspace
          </button>
        </div>
      </header>

      {/* Main Security Settings Panel */}
      <main className="main-content page-container flex-center-pt10">
        <div className="glass-panel panel-auth-setting">

          <div className="flex-align-center-gap3-mb2">
            <svg width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" className="text-primary">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
            <h2 className="title-setting">Security Settings</h2>
          </div>
          <p className="text-muted-desc-lg">
            Configure and manage safety credentials for legal document accesses
          </p>

          {successMsg && (
            <div className="alert alert-success mb-6">
              {successMsg}
            </div>
          )}

          {errorMsg && (
            <div className="alert alert-danger mb-6">
              {errorMsg}
            </div>
          )}

          {/* STEP 1: Status View */}
          {step === "status" && (
            <div>
              {user?.is_2fa_enabled ? (
                <div>
                  <div className="status-card-active">
                    <div className="status-title-active">
                      <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Two-Factor Authentication is Active
                    </div>
                    <p className="status-desc-active">
                      Verification email codes will be delivered to: <strong className="text-secondary-color">{maskEmail(user?.email)}</strong>
                    </p>
                  </div>

                  <div className="section-danger-zone">
                    <h4 className="title-section-sm">Disable 2FA</h4>
                    <p className="text-muted-sm mb-5">
                      If you disable two-factor authentication, you will only need your email and password to log in. This lowers your account security.
                    </p>
                    <button
                      onClick={handleDisable2FA}
                      disabled={isSubmitting}
                      className="btn btn-secondary btn-danger-outline"
                    >
                      Disable 2FA
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex-column-gap1-mb6">
                    <h3 className="title-subsection">Enable Two-Factor Authentication (2FA)</h3>
                    <p className="text-muted-sm">
                      We'll send a 6-digit verification code to your registered email (<strong className="text-main">{maskEmail(user?.email)}</strong>) each time you log in, ensuring that only you can access your legal workspace.
                    </p>
                  </div>
                  <button
                    onClick={handleEnable2FA}
                    disabled={isSubmitting}
                    className="btn btn-primary w-full"
                  >
                    {isSubmitting ? <div className="spinner spinner-sm" /> : "Enable Email 2FA"}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: OTP Verification Form */}
          {step === "verify" && (
            <div>
              <div className="flex-column-gap1-mb5">
                <h3 className="title-subsection">Verify Your Email</h3>
                <p className="text-muted-sm">
                  Enter the 6-digit OTP code sent to <strong className="text-main">{maskEmail(user?.email)}</strong>. Code expires in: <span className="countdown-timer">{formatExpiryTime(otpExpirySeconds)}</span>
                </p>
              </div>

              <div className="otp-container">
                {otpDigits.map((digit, idx) => (
                  <input
                    key={idx}
                    ref={(el) => { inputRefs.current[idx] = el; }}
                    type="text"
                    maxLength={6}
                    value={digit}
                    className="otp-digit-input"
                    onChange={(e) => handleOtpChange(idx, e.target.value)}
                    onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                    disabled={isSubmitting}
                    title={`Verification digit ${idx + 1}`}
                    placeholder="-"
                  />
                ))}
              </div>

              {otpExpirySeconds <= 0 && (
                <div className="alert alert-danger alert-expired">
                  The code has expired. Please go back and request a new code.
                </div>
              )}

              <div className="flex-gap3-mt10">
                <button
                  onClick={() => verifyOtpCode()}
                  disabled={isSubmitting || otpDigits.join("").length !== 6 || otpExpirySeconds <= 0}
                  className="btn btn-primary flex-1"
                >
                  {isSubmitting ? <div className="spinner spinner-sm" /> : "Verify & Activate"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStep("status");
                    setErrorMsg(null);
                  }}
                  className="btn btn-secondary"
                  disabled={isSubmitting}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

        {/* ACTIVE SESSIONS PANEL */}
        <div className="sessions-section">
          <div className="sessions-header">
            <h3 className="sessions-title">Active Device Sessions</h3>
            {sessions.length > 1 && (
              <button
                onClick={handleRevokeOthers}
                className="btn btn-secondary btn-nav-action"
                style={{ color: "var(--color-danger)", borderColor: "rgba(244, 63, 94, 0.2)" }}
              >
                Log Out Other Devices
              </button>
            )}
          </div>

          {isLoadingSessions ? (
            <div className="flex-center-pt10" style={{ paddingTop: "20px" }}>
              <div className="spinner spinner-sm" />
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-muted-sm">No active sessions found.</p>
          ) : (
            <div className="sessions-list">
              {sessions.map((s) => (
                <div key={s.id} className="session-item">
                  <div className="session-info">
                    <div className="session-device">
                      {s.device_info || "Unknown Device / Browser"}
                    </div>
                    <div className="session-meta">
                      <span>IP: {s.ip_address || "Unknown"}</span>
                      <span>•</span>
                      <span>
                        Last active: {new Date(s.last_active_at).toLocaleString()}
                      </span>
                      {s.is_current && (
                        <span className="session-tag-current">This Device</span>
                      )}
                    </div>
                  </div>
                  <div className="session-actions">
                    <button
                      onClick={() => handleRevokeSession(s.id, s.is_current)}
                      className="btn btn-secondary btn-table-action btn-danger-outline"
                    >
                      {s.is_current ? "Log Out" : "Revoke"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        </div>
      </main>
    </div>
  );
};
