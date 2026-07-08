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

  // Web OTP API for auto-fill on mobile
  useEffect(() => {
    if (step !== "verify" || !("OTPCredential" in window)) return;

    const ac = new AbortController();
    navigator.credentials
      .get({
        otp: { transport: ["sms"] },
        signal: ac.signal,
      } as any)
      .then((otp: any) => {
        if (otp && otp.code) {
          const digits = otp.code.slice(0, 6).split("");
          const newDigits = ["", "", "", "", "", ""];
          for (let i = 0; i < digits.length; i++) {
            newDigits[i] = digits[i];
          }
          setOtpDigits(newDigits);

          if (otp.code.length === 6) {
            verifyOtpCode(otp.code);
          }
        }
      })
      .catch((err) => {
        console.log("Web OTP error:", err);
      });

    return () => {
      ac.abort();
    };
  }, [step]);

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
        <div className="navbar-brand">
          Legal<span>Intelligence</span>
        </div>
        <div className="navbar-actions">
          <span className="user-email">{user?.email}</span>
          <button onClick={() => navigate("/dashboard")} className="btn btn-secondary" style={{ padding: "8px 16px", fontSize: "0.85rem" }}>
            Workspace
          </button>
        </div>
      </header>

      {/* Main Security Settings Panel */}
      <main className="main-content page-container" style={{ display: "flex", justifyContent: "center", paddingTop: "40px" }}>
        <div className="glass-panel" style={{ width: "100%", maxWidth: "560px", padding: "40px" }}>

          <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "8px" }}>
            <svg width="28" height="28" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ color: "var(--color-primary)" }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
            <h2 style={{ fontSize: "1.6rem", fontWeight: 700 }}>Security Settings</h2>
          </div>
          <p style={{ fontSize: "0.9rem", color: "var(--color-text-muted)", marginBottom: "30px" }}>
            Configure and manage safety credentials for legal document accesses
          </p>

          {successMsg && (
            <div className="alert alert-success" style={{ marginBottom: "24px" }}>
              {successMsg}
            </div>
          )}

          {errorMsg && (
            <div className="alert alert-danger" style={{ marginBottom: "24px" }}>
              {errorMsg}
            </div>
          )}

          {/* STEP 1: Status View */}
          {step === "status" && (
            <div>
              {user?.is_2fa_enabled ? (
                <div>
                  <div className="alert alert-success" style={{ background: "rgba(16, 185, 129, 0.05)", border: "1px solid rgba(16, 185, 129, 0.2)", display: "flex", flexDirection: "column", alignItems: "flex-start", gap: "8px", padding: "20px", borderRadius: "12px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--color-success)", fontWeight: 700, fontSize: "1.05rem" }}>
                      <svg width="20" height="20" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Two-Factor Authentication is Active
                    </div>
                    <p style={{ color: "var(--color-text-main)", fontSize: "0.9rem", margin: 0 }}>
                      Verification email codes will be delivered to: <strong style={{ color: "var(--color-secondary)" }}>{maskEmail(user?.email)}</strong>
                    </p>
                  </div>

                  <div style={{ marginTop: "30px", borderTop: "1px solid var(--color-border)", paddingTop: "20px" }}>
                    <h4 style={{ fontSize: "1.05rem", marginBottom: "8px" }}>Disable 2FA</h4>
                    <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)", marginBottom: "20px" }}>
                      If you disable two-factor authentication, you will only need your email and password to log in. This lowers your account security.
                    </p>
                    <button
                      onClick={handleDisable2FA}
                      disabled={isSubmitting}
                      className="btn btn-secondary"
                      style={{ color: "var(--color-danger)", borderColor: "rgba(239, 68, 68, 0.2)" }}
                    >
                      Disable 2FA
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "24px" }}>
                    <h3 style={{ fontSize: "1.15rem", fontWeight: 600 }}>Enable Two-Factor Authentication (2FA)</h3>
                    <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
                      We'll send a 6-digit verification code to your registered email (<strong style={{ color: "var(--color-text-main)" }}>{maskEmail(user?.email)}</strong>) each time you log in, ensuring that only you can access your legal workspace.
                    </p>
                  </div>
                  <button
                    onClick={handleEnable2FA}
                    disabled={isSubmitting}
                    className="btn btn-primary"
                    style={{ width: "100%" }}
                  >
                    {isSubmitting ? <div className="spinner" style={{ width: "18px", height: "18px" }} /> : "Enable Email 2FA"}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: OTP Verification Form */}
          {step === "verify" && (
            <div>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "20px" }}>
                <h3 style={{ fontSize: "1.15rem", fontWeight: 600 }}>Verify Your Email</h3>
                <p style={{ fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
                  Enter the 6-digit OTP code sent to <strong style={{ color: "var(--color-text-main)" }}>{maskEmail(user?.email)}</strong>. Code expires in: <span className="countdown-timer">{formatExpiryTime(otpExpirySeconds)}</span>
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
                  />
                ))}
              </div>

              {otpExpirySeconds <= 0 && (
                <div className="alert alert-danger" style={{ fontSize: "0.8rem", padding: "10px", marginTop: "10px" }}>
                  The code has expired. Please go back and request a new code.
                </div>
              )}

              <div style={{ display: "flex", gap: "12px", marginTop: "30px" }}>
                <button
                  onClick={() => verifyOtpCode()}
                  disabled={isSubmitting || otpDigits.join("").length !== 6 || otpExpirySeconds <= 0}
                  className="btn btn-primary"
                  style={{ flex: 1 }}
                >
                  {isSubmitting ? <div className="spinner" style={{ width: "18px", height: "18px" }} /> : "Verify & Activate"}
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

        </div>
      </main>
    </div>
  );
};
