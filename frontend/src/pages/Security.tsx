import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { useAuthStore } from "../store/useAuthStore";
import {
  downloadAccountExport,
  getRetentionPolicy,
  updateRetentionPolicy,
  requestAccountDeletionOTP,
  deleteAccount,
} from "../services/accountService";

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

  // Data Portability & Export State
  const [isExporting, setIsExporting] = useState(false);

  // Data Retention State
  const [retentionDays, setRetentionDays] = useState<number | null>(null);
  const [selectedRetention, setSelectedRetention] = useState<string>("null");
  const [isSavingRetention, setIsSavingRetention] = useState(false);
  const [isLoadingRetention, setIsLoadingRetention] = useState(false);
  const [retentionMsg, setRetentionMsg] = useState<string | null>(null);

  // Danger Zone / Account Deletion State
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteOtp, setDeleteOtp] = useState("");
  const [isRequestingDeleteOtp, setIsRequestingDeleteOtp] = useState(false);
  const [deleteOtpSent, setDeleteOtpSent] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [deleteModalError, setDeleteModalError] = useState<string | null>(null);

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

  const fetchRetention = async () => {
    setIsLoadingRetention(true);
    try {
      const data = await getRetentionPolicy();
      setRetentionDays(data.data_retention_days);
      setSelectedRetention(data.data_retention_days === null ? "null" : String(data.data_retention_days));
    } catch (err) {
      console.error("Failed to load retention policy", err);
    } finally {
      setIsLoadingRetention(false);
    }
  };

  useEffect(() => {
    fetchRetention();
  }, []);

  const handleExportData = async () => {
    setIsExporting(true);
    setErrorMsg(null);
    try {
      await downloadAccountExport();
      setSuccessMsg("Account data archive successfully exported and downloaded.");
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Failed to generate account data export.");
    } finally {
      setIsExporting(false);
    }
  };

  const handleSaveRetention = async () => {
    setIsSavingRetention(true);
    setRetentionMsg(null);
    setErrorMsg(null);
    try {
      const days = selectedRetention === "null" ? null : parseInt(selectedRetention, 10);
      const res = await updateRetentionPolicy(days);
      setRetentionDays(res.data_retention_days);
      setRetentionMsg(
        res.purged_logs_count > 0
          ? `Retention policy updated. ${res.purged_logs_count} older audit log(s) purged.`
          : "Data retention policy updated successfully."
      );
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || "Failed to update retention policy.");
    } finally {
      setIsSavingRetention(false);
    }
  };

  const handleRequestDeleteOtp = async () => {
    setIsRequestingDeleteOtp(true);
    setDeleteModalError(null);
    try {
      await requestAccountDeletionOTP();
      setDeleteOtpSent(true);
    } catch (err: any) {
      setDeleteModalError(err.response?.data?.detail || "Failed to dispatch verification code.");
    } finally {
      setIsRequestingDeleteOtp(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletePassword) {
      setDeleteModalError("Please enter your account password.");
      return;
    }
    if (!deleteOtp || deleteOtp.trim().length !== 6) {
      setDeleteModalError("Please enter the 6-digit verification code sent to your email.");
      return;
    }

    setIsDeletingAccount(true);
    setDeleteModalError(null);
    try {
      await deleteAccount(deletePassword, deleteOtp.trim());
      const logout = useAuthStore.getState().logout;
      await logout();
      navigate("/login?account_deleted=true");
    } catch (err: any) {
      setDeleteModalError(err.response?.data?.detail || "Account deletion failed. Please check credentials.");
      setIsDeletingAccount(false);
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
    <>
      <div className="security-page-content" style={{ display: "flex", justifyContent: "center", width: "100%" }}>
      <div className="glass-panel panel-auth-setting" style={{ maxWidth: "680px", width: "100%" }}>

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

        {/* DATA PORTABILITY & EXPORT PANEL */}
        <div className="sessions-section">
          <div className="sessions-header">
            <div>
              <h3 className="sessions-title">Data Portability & Export</h3>
              <p className="text-muted-sm" style={{ marginTop: "4px" }}>
                Export a comprehensive JSON archive containing all your contracts, analyses, Q&A threads with clause citations, and activity logs.
              </p>
            </div>
          </div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(255, 255, 255, 0.02)", border: "1px solid var(--color-border)", borderRadius: "12px", padding: "16px" }}>
            <div>
              <div style={{ fontWeight: 500, color: "var(--color-text-main)", fontSize: "0.925rem" }}>
                Account Data Archive (.json)
              </div>
              <div className="text-muted-sm">
                Generated per GDPR Article 20 / CCPA data portability standards.
              </div>
            </div>
            <button
              onClick={handleExportData}
              disabled={isExporting}
              className="btn btn-secondary btn-nav-action"
              style={{ display: "flex", alignItems: "center", gap: "8px" }}
            >
              {isExporting ? (
                <>
                  <div className="spinner spinner-sm" />
                  <span>Exporting...</span>
                </>
              ) : (
                <>
                  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                  <span>Export JSON</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* DATA RETENTION POLICY PANEL */}
        <div className="sessions-section">
          <div className="sessions-header">
            <div>
              <h3 className="sessions-title">Activity History Retention</h3>
              <p className="text-muted-sm" style={{ marginTop: "4px" }}>
                Set an automatic expiration window for your activity audit timeline. Older entries are permanently purged.
              </p>
            </div>
          </div>

          {retentionMsg && (
            <div className="alert alert-success mb-4" style={{ padding: "10px 14px", fontSize: "0.875rem" }}>
              {retentionMsg}
            </div>
          )}

          <div style={{ background: "rgba(255, 255, 255, 0.02)", border: "1px solid var(--color-border)", borderRadius: "12px", padding: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
              <div style={{ flex: "1 1 250px" }}>
                <label htmlFor="retention-select" style={{ display: "block", fontSize: "0.875rem", fontWeight: 500, marginBottom: "6px", color: "var(--color-text-main)" }}>
                  Log Retention Duration
                </label>
                <select
                  id="retention-select"
                  value={selectedRetention}
                  onChange={(e) => setSelectedRetention(e.target.value)}
                  disabled={isLoadingRetention || isSavingRetention}
                  style={{
                    width: "100%",
                    maxWidth: "280px",
                    background: "rgba(0, 0, 0, 0.3)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "8px",
                    padding: "8px 12px",
                    color: "var(--color-text-main)",
                    fontSize: "0.9rem",
                  }}
                >
                  <option value="null">Indefinite (Keep all history)</option>
                  <option value="30">30 Days (1 Month)</option>
                  <option value="90">90 Days (3 Months)</option>
                  <option value="180">180 Days (6 Months)</option>
                  <option value="365">365 Days (1 Year)</option>
                </select>
              </div>
              <button
                onClick={handleSaveRetention}
                disabled={isSavingRetention || isLoadingRetention}
                className="btn btn-primary"
                style={{ padding: "8px 18px", alignSelf: "flex-end" }}
              >
                {isSavingRetention ? <div className="spinner spinner-sm" /> : "Save Retention"}
              </button>
            </div>
            <div className="text-muted-sm" style={{ marginTop: "10px", fontSize: "0.8rem" }}>
              Current Policy: <strong>{retentionDays === null ? "Indefinite Retention" : `${retentionDays} Days`}</strong>
            </div>
          </div>
        </div>

        {/* DANGER ZONE: ACCOUNT DELETION */}
        <div className="sessions-section" style={{ borderColor: "rgba(239, 68, 68, 0.3)" }}>
          <div className="sessions-header">
            <div>
              <h3 className="sessions-title" style={{ color: "var(--color-danger, #ef4444)" }}>
                Danger Zone
              </h3>
              <p className="text-muted-sm" style={{ marginTop: "4px" }}>
                Irreversible account operations and complete personal data destruction.
              </p>
            </div>
          </div>

          <div style={{ background: "rgba(239, 68, 68, 0.04)", border: "1px solid rgba(239, 68, 68, 0.2)", borderRadius: "12px", padding: "16px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <div style={{ fontWeight: 600, color: "var(--color-text-main)", fontSize: "0.95rem" }}>
                Permanently Delete Account
              </div>
              <p className="text-muted-sm" style={{ maxWidth: "440px", marginTop: "4px", fontSize: "0.825rem" }}>
                Immediately erases your login credentials, active sessions, uploaded contract documents, analyses, and Q&A conversation threads. Compliance audit logs are pseudonymized.
              </p>
            </div>
            <button
              onClick={() => {
                setShowDeleteModal(true);
                setDeleteModalError(null);
                setDeletePassword("");
                setDeleteOtp("");
                setDeleteOtpSent(false);
              }}
              className="btn btn-secondary btn-danger-outline"
              style={{ color: "var(--color-danger, #ef4444)", borderColor: "rgba(239, 68, 68, 0.4)", padding: "8px 16px" }}
            >
              Delete Account
            </button>
          </div>
        </div>

        </div>
      </div>

      {/* ACCOUNT DELETION VERIFICATION MODAL */}
      {showDeleteModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            className="glass-panel"
            style={{
              maxWidth: "500px",
              width: "100%",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              background: "#12131a",
              borderRadius: "16px",
              padding: "28px",
              boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.7)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "16px" }}>
              <div
                style={{
                  background: "rgba(239, 68, 68, 0.15)",
                  color: "#ef4444",
                  width: "44px",
                  height: "44px",
                  borderRadius: "10px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700, color: "#ef4444" }}>
                  Confirm Permanent Deletion
                </h3>
                <p className="text-muted-sm" style={{ margin: 0, fontSize: "0.825rem" }}>
                  Dual-factor verification required
                </p>
              </div>
            </div>

            <p style={{ fontSize: "0.875rem", color: "var(--color-text-muted)", marginBottom: "20px", lineHeight: "1.5" }}>
              This will permanently delete your account and all associated documents, embeddings, and chat history. This action <strong>cannot</strong> be undone.
            </p>

            {deleteModalError && (
              <div className="alert alert-danger mb-4" style={{ padding: "10px 14px", fontSize: "0.85rem" }}>
                {deleteModalError}
              </div>
            )}

            {/* Step 1: Account Password */}
            <div style={{ marginBottom: "16px" }}>
              <label style={{ display: "block", fontSize: "0.85rem", fontWeight: 500, marginBottom: "6px", color: "var(--color-text-main)" }}>
                Current Password
              </label>
              <input
                type="password"
                placeholder="Enter your account password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                disabled={isDeletingAccount}
                style={{
                  width: "100%",
                  background: "rgba(0, 0, 0, 0.3)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  padding: "10px 12px",
                  color: "var(--color-text-main)",
                  fontSize: "0.9rem",
                }}
              />
            </div>

            {/* Step 2: Email OTP */}
            <div style={{ marginBottom: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
                <label style={{ fontSize: "0.85rem", fontWeight: 500, color: "var(--color-text-main)" }}>
                  Security Verification Code (Email OTP)
                </label>
                <button
                  type="button"
                  onClick={handleRequestDeleteOtp}
                  disabled={isRequestingDeleteOtp || isDeletingAccount}
                  style={{
                    background: "none",
                    border: "none",
                    color: "var(--color-primary, #6366f1)",
                    cursor: "pointer",
                    fontSize: "0.8rem",
                    padding: 0,
                    textDecoration: "underline",
                  }}
                >
                  {isRequestingDeleteOtp ? "Sending..." : deleteOtpSent ? "Resend Code" : "Send Verification Code"}
                </button>
              </div>
              <input
                type="text"
                maxLength={6}
                placeholder="Enter 6-digit code"
                value={deleteOtp}
                onChange={(e) => setDeleteOtp(e.target.value.replace(/\D/g, ""))}
                disabled={isDeletingAccount}
                style={{
                  width: "100%",
                  letterSpacing: "4px",
                  textAlign: "center",
                  fontWeight: 600,
                  fontSize: "1.1rem",
                  background: "rgba(0, 0, 0, 0.3)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  padding: "10px 12px",
                  color: "var(--color-text-main)",
                }}
              />
              {deleteOtpSent && (
                <p style={{ fontSize: "0.775rem", color: "#10b981", marginTop: "6px" }}>
                  ✓ Verification code sent to {maskEmail(user?.email)}. Valid for 5 minutes.
                </p>
              )}
            </div>

            {/* Actions */}
            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
              <button
                type="button"
                onClick={() => {
                  if (!isDeletingAccount) {
                    setShowDeleteModal(false);
                    setDeleteModalError(null);
                  }
                }}
                className="btn btn-secondary"
                disabled={isDeletingAccount}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={isDeletingAccount || !deletePassword || deleteOtp.length !== 6}
                className="btn btn-danger"
                style={{
                  background: "#ef4444",
                  borderColor: "#ef4444",
                  color: "#fff",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                {isDeletingAccount ? (
                  <>
                    <div className="spinner spinner-sm" />
                    <span>Deleting Account...</span>
                  </>
                ) : (
                  "Permanently Delete Account"
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
