import React, { useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams, useLocation, Link } from "react-router-dom";
import api from "../services/api";
import { useAuthStore, type User } from "../store/useAuthStore";

declare global {
  interface Window {
    google?: any;
  }
}

interface LoginFormData {
  email: string;
  password: string;
}

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const login = useAuthStore((state) => state.login);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showExpiredAlert, setShowExpiredAlert] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // 2FA login state
  const [requires2fa, setRequires2fa] = useState(false);
  const [pendingToken, setPendingToken] = useState<string | null>(null);
  const [maskedMessage, setMaskedMessage] = useState("");
  const [otpDigits, setOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [otpExpirySeconds, setOtpExpirySeconds] = useState(300); // 5 minutes
  const [otpSuccessMsg, setOtpSuccessMsg] = useState<string | null>(null);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Where to redirect after login (preserve attempted route)
  const fromPath = (location.state as any)?.from?.pathname || "/dashboard";

  const handleGoogleCredentialResponse = async (response: any) => {
    setErrorMsg(null);
    setIsSubmitting(true);
    setShowExpiredAlert(false);

    try {
      const res = await api.post("/auth/google-login", {
        credential: response.credential,
      });

      const { access_token, refresh_token } = res.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      const userResponse = await api.get<User>("/auth/me");
      const user = userResponse.data;

      login(access_token, refresh_token, user);
      navigate(fromPath, { replace: true });
    } catch (err: any) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Google Sign-In failed. Please try logging in with your email and password.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Initialize Google Sign-In SDK
  useEffect(() => {
    if (requires2fa) return;

    let intervalId: any;

    let fetchedClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID;

    const initGoogle = async () => {
      const google = window.google;

      if (!fetchedClientId) {
        try {
          const res = await api.get("/auth/oauth-config");
          if (res.data?.google_client_id) {
            fetchedClientId = res.data.google_client_id;
          }
        } catch {
          // ignore network errors if backend is booting
        }
      }

      if (google && fetchedClientId) {
        google.accounts.id.initialize({
          client_id: fetchedClientId,
          callback: handleGoogleCredentialResponse,
        });

        const btnElement = document.getElementById("google-signin-btn");
        if (btnElement) {
          google.accounts.id.renderButton(btnElement, {
            theme: "outline",
            size: "large",
            type: "standard",
            shape: "rectangular",
            text: "signin_with",
            logo_alignment: "left",
            width: 320,
          });
        }
        if (intervalId) clearInterval(intervalId);
      }
    };

    initGoogle();

    let attempts = 0;
    intervalId = setInterval(() => {
      attempts++;
      initGoogle();
      if (attempts > 25) {
        clearInterval(intervalId);
      }
    }, 200);

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [requires2fa]);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormData>();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate(fromPath, { replace: true });
    }
  }, [isAuthenticated, navigate, fromPath]);

  // Check if redirected due to session expiry
  useEffect(() => {
    if (searchParams.get("expired") === "true") {
      setShowExpiredAlert(true);
    }
  }, [searchParams]);

  // Handle 30-second cooldown timer
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setTimeout(() => {
      setResendCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearTimeout(timer);
  }, [resendCooldown]);

  // Handle 5-minute OTP countdown timer
  useEffect(() => {
    if (!requires2fa || otpExpirySeconds <= 0) return;
    const timer = setTimeout(() => {
      setOtpExpirySeconds((prev) => prev - 1);
    }, 1000);
    return () => clearTimeout(timer);
  }, [requires2fa, otpExpirySeconds]);

  // Auto-focus first OTP digit when 2FA modal opens
  useEffect(() => {
    if (requires2fa) {
      setTimeout(() => {
        inputRefs.current[0]?.focus();
      }, 100);
    }
  }, [requires2fa]);

  const onSubmit = async (data: LoginFormData) => {
    setErrorMsg(null);
    setIsSubmitting(true);
    setShowExpiredAlert(false);

    try {
      const response = await api.post("/auth/login", {
        email: data.email,
        password: data.password,
      });

      const { access_token, refresh_token, requires_2fa, pending_2fa_token, message } =
        response.data;

      // If user requires two-factor authentication
      if (requires_2fa) {
        setPendingToken(pending_2fa_token);
        setMaskedMessage(
          message || "Enter the 6-digit verification code sent to your registered email address."
        );
        setRequires2fa(true);
        setResendCooldown(30);
        setOtpExpirySeconds(300);
        setOtpDigits(["", "", "", "", "", ""]);
        return;
      }

      // Temporary token storage so interceptor can fetch profile
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      const userResponse = await api.get<User>("/auth/me");
      const user = userResponse.data;

      login(access_token, refresh_token, user);
      navigate(fromPath, { replace: true });
    } catch (err: any) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Failed to connect to the server. Please check your network connection.");
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

      // Auto-submit if all 6 digits are populated
      if (newDigits.every((d) => d.length === 1)) {
        handle2faVerify(newDigits.join(""));
      }
    } else {
      newDigits[index] = value;
      setOtpDigits(newDigits);
      if (value && index < 5) {
        inputRefs.current[index + 1]?.focus();
      }

      // Auto-submit when 6th digit entered
      if (value && index === 5 && newDigits.every((d) => d.length === 1)) {
        handle2faVerify(newDigits.join(""));
      }
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !otpDigits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handle2faVerify = async (codeOverride?: string) => {
    const code = codeOverride || otpDigits.join("");
    if (code.length !== 6) {
      setErrorMsg("Please enter all 6 digits of the verification code.");
      return;
    }
    setErrorMsg(null);
    setOtpSuccessMsg(null);
    setIsSubmitting(true);

    try {
      const response = await api.post("/auth/2fa/login-verify", {
        pending_2fa_token: pendingToken,
        otp_code: code,
      });

      const { access_token, refresh_token } = response.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      const userResponse = await api.get<User>("/auth/me");
      const user = userResponse.data;

      login(access_token, refresh_token, user);
      navigate(fromPath, { replace: true });
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Verification code is invalid or expired. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResendOtp = async () => {
    if (resendCooldown > 0) return;
    setErrorMsg(null);
    setOtpSuccessMsg(null);

    try {
      await api.post("/auth/2fa/resend-otp", {
        pending_2fa_token: pendingToken,
      });
      setOtpSuccessMsg("A new verification code has been dispatched to your email.");
      setResendCooldown(30);
      setOtpExpirySeconds(300);
      setOtpDigits(["", "", "", "", "", ""]);
      inputRefs.current[0]?.focus();
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Failed to resend code. Please wait a moment and try again.");
      }
    }
  };

  const fillDemoCredentials = () => {
    setValue("email", "lawyer@example.com");
    setValue("password", "SecurePassword123!");
    setErrorMsg(null);
  };

  // Render 2FA verification panel
  if (requires2fa) {
    const mins = Math.floor(otpExpirySeconds / 60);
    const secs = otpExpirySeconds % 60;
    const formattedTime = `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;

    return (
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <header className="navbar">
          <div onClick={() => navigate("/")} className="navbar-brand" style={{ cursor: "pointer" }}>
            Legal<span>Intelligence</span>
          </div>
        </header>

        <div className="auth-container" style={{ flex: 1 }}>
          <div className="glass-panel auth-card">
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "50%",
                background: "rgba(92, 98, 236, 0.12)",
                color: "var(--color-primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 16px auto",
              }}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>

            <h2 className="auth-title">Two-Factor Authentication</h2>
            <p className="auth-subtitle">{maskedMessage}</p>

            {otpSuccessMsg && <div className="alert alert-success">{otpSuccessMsg}</div>}
            {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}

            <div style={{ textAlign: "center", marginBottom: "12px", fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
              Code expires in:{" "}
              <strong style={{ color: otpExpirySeconds < 60 ? "var(--color-danger)" : "var(--color-primary)" }}>
                {formattedTime}
              </strong>
            </div>

            <div className="otp-container">
              {otpDigits.map((digit, idx) => (
                <input
                  key={idx}
                  ref={(el) => {
                    inputRefs.current[idx] = el;
                  }}
                  type="text"
                  inputMode="numeric"
                  pattern="[0-9]*"
                  maxLength={6}
                  value={digit}
                  className="otp-digit-input"
                  onChange={(e) => handleOtpChange(idx, e.target.value)}
                  onKeyDown={(e) => handleOtpKeyDown(idx, e)}
                  disabled={isSubmitting || otpExpirySeconds <= 0}
                  title={`Verification digit ${idx + 1}`}
                  placeholder="•"
                />
              ))}
            </div>

            <button
              onClick={() => handle2faVerify()}
              disabled={isSubmitting || otpExpirySeconds <= 0}
              className="btn btn-primary w-full mt-3"
            >
              {isSubmitting ? <div className="spinner spinner-sm" /> : "Verify & Sign In"}
            </button>

            <div className="auth-footer mt-6">
              Didn't receive the code?{" "}
              {resendCooldown > 0 ? (
                <span className="text-dark">Resend in {resendCooldown}s</span>
              ) : (
                <button onClick={handleResendOtp} className="btn-inline-primary">
                  Resend Code
                </button>
              )}
            </div>

            <div className="auth-footer mt-3">
              <button
                onClick={() => {
                  setRequires2fa(false);
                  setPendingToken(null);
                  setErrorMsg(null);
                  setOtpSuccessMsg(null);
                  setOtpDigits(["", "", "", "", "", ""]);
                }}
                className="btn-inline-muted"
              >
                ← Back to Login
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render standard login form
  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header className="navbar">
        <div onClick={() => navigate("/")} className="navbar-brand" style={{ cursor: "pointer" }}>
          Legal<span>Intelligence</span>
        </div>
      </header>

      <div className="auth-container" style={{ flex: 1 }}>
        <div className="glass-panel auth-card">
          <h2 className="auth-title">Welcome Back</h2>
          <p className="auth-subtitle">Log in to review, analyze, and negotiate your contracts</p>

          {showExpiredAlert && (
            <div className="alert alert-warning">
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
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>Your session expired due to inactivity. Please sign in again.</span>
            </div>
          )}

          {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}

          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="form-group">
              <label className="form-label" htmlFor="email">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                placeholder="name@company.com"
                className={`form-control ${errors.email ? "is-invalid" : ""}`}
                {...register("email", {
                  required: "Email is required",
                  pattern: {
                    value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                    message: "Please enter a valid email address",
                  },
                })}
              />
              {errors.email && <span className="error-msg-text">{errors.email.message}</span>}
            </div>

            <div className="form-group">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <label className="form-label" htmlFor="password">
                  Password
                </label>
              </div>
              <div className="input-password-wrapper">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  className={`form-control ${errors.password ? "is-invalid" : ""}`}
                  {...register("password", {
                    required: "Password is required",
                  })}
                />
                <button
                  type="button"
                  className="btn-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  title={showPassword ? "Hide password" : "Show password"}
                  aria-label="Toggle password visibility"
                >
                  {showPassword ? (
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
                      <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
                      <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
                      <path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
                      <line x1="2" y1="2" x2="22" y2="22" />
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
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  )}
                </button>
              </div>
              {errors.password && <span className="error-msg-text">{errors.password.message}</span>}
            </div>

            <button type="submit" disabled={isSubmitting} className="btn btn-primary w-full mt-3">
              {isSubmitting ? <div className="spinner spinner-sm" /> : "Sign In"}
            </button>
          </form>

          {/* Quick Demo Credentials Pill */}
          <div className="auth-demo-pill" onClick={fillDemoCredentials} title="Click to fill test credentials">
            <span>
              💡 <strong>Demo Login:</strong> lawyer@example.com
            </span>
            <span style={{ color: "var(--color-primary)", fontWeight: "600" }}>Auto-Fill</span>
          </div>

          <div className="auth-divider">
            <span>or</span>
          </div>

          <div className="google-btn-wrapper">
            <div id="google-signin-btn"></div>
          </div>

          <div className="auth-footer">
            Don't have an account? <Link to="/register">Create one free</Link>
          </div>
        </div>
      </div>
    </div>
  );
};
