import React, { useState, useEffect, useRef } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
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
  const [searchParams] = useSearchParams();
  const login = useAuthStore((state) => state.login);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showExpiredAlert, setShowExpiredAlert] = useState(false);

  // 2FA login state
  const [requires2fa, setRequires2fa] = useState(false);
  const [pendingToken, setPendingToken] = useState<string | null>(null);
  const [maskedMessage, setMaskedMessage] = useState("");
  const [otpDigits, setOtpDigits] = useState<string[]>(["", "", "", "", "", ""]);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [otpSuccessMsg, setOtpSuccessMsg] = useState<string | null>(null);

  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  const handleGoogleCredentialResponse = async (response: any) => {
    setErrorMsg(null);
    setIsSubmitting(true);
    setShowExpiredAlert(false);

    try {
      const res = await api.post("/auth/google-login", {
        credential: response.credential,
      });

      const { access_token, refresh_token } = res.data;

      // Temporary token storage so interceptor can fetch profile
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      // Fetch user profile
      const userResponse = await api.get<User>("/auth/me");
      const user = userResponse.data;

      // Save to Zustand store
      login(access_token, refresh_token, user);
      
      // Redirect to dashboard
      navigate("/dashboard");
    } catch (err: any) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Google Sign-In failed. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Initialize Google Sign-In SDK
  useEffect(() => {
    if (requires2fa) return;

    let intervalId: any;

    const initGoogle = () => {
      const google = window.google;
      const client_id = import.meta.env.VITE_GOOGLE_CLIENT_ID;

      if (google && client_id) {
        google.accounts.id.initialize({
          client_id: client_id,
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

    // Try initiating immediately
    initGoogle();

    // Poll every 200ms until loaded (max 5 seconds)
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
    formState: { errors },
  } = useForm<LoginFormData>();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard");
    }
  }, [isAuthenticated, navigate]);

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




  const onSubmit = async (data: LoginFormData) => {
    setErrorMsg(null);
    setIsSubmitting(true);
    setShowExpiredAlert(false);

    try {
      // 1. Authenticate with backend
      const response = await api.post("/auth/login", {
        email: data.email,
        password: data.password,
      });
      
      const { access_token, refresh_token, requires_2fa, pending_2fa_token, message } = response.data;

      // If user requires two-factor authentication
      if (requires_2fa) {
        setPendingToken(pending_2fa_token);
        setMaskedMessage(message || "Enter the verification code sent to your registered email address.");
        setRequires2fa(true);
        setResendCooldown(30);
        return;
      }

      // Temporary token storage so interceptor can fetch profile
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      // 2. Fetch user profile
      const userResponse = await api.get<User>("/auth/me");
      const user = userResponse.data;

      // 3. Save to Zustand store
      login(access_token, refresh_token, user);
      
      // Redirect to dashboard
      navigate("/dashboard");
    } catch (err: any) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Failed to connect to the server. Please try again later.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return; // numeric only
    const newDigits = [...otpDigits];
    
    // If user pasted or typed multiple digits
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

      // Temporary token storage so interceptor can fetch profile
      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      // Fetch user profile
      const userResponse = await api.get<User>("/auth/me");
      const user = userResponse.data;

      // Save to Zustand store
      login(access_token, refresh_token, user);
      
      // Redirect to dashboard
      navigate("/dashboard");
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Verification failed. Please try again.");
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
      setOtpSuccessMsg("A new verification code has been sent.");
      setResendCooldown(30);
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Failed to resend code. Please try again.");
      }
    }
  };

  // Render 2FA verification panel
  if (requires2fa) {
    return (
      <div className="auth-container">
        <div className="glass-panel auth-card">
          <h2 className="auth-title">Enter Verification Code</h2>
          <p className="auth-subtitle">{maskedMessage}</p>

          {otpSuccessMsg && (
            <div className="alert alert-success">
              {otpSuccessMsg}
            </div>
          )}

          {errorMsg && (
            <div className="alert alert-danger">
              {errorMsg}
            </div>
          )}
          <div>
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

            <button
              onClick={() => handle2faVerify()}
              disabled={isSubmitting}
              className="btn btn-primary w-full mt-3"
            >
              {isSubmitting ? (
                <div className="spinner spinner-sm" />
              ) : (
                "Verify & Log In"
              )}
            </button>

            <div className="auth-footer mt-6">
              Didn't receive the code?{" "}
              {resendCooldown > 0 ? (
                <span className="text-dark">
                  Resend code in {resendCooldown}s
                </span>
              ) : (
                <button
                  onClick={handleResendOtp}
                  className="btn-inline-primary"
                >
                  Resend code
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
                Back to Login
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Render standard login form
  return (
    <div className="auth-container">
      <div className="glass-panel auth-card">
        <h2 className="auth-title">Welcome Back</h2>
        <p className="auth-subtitle">Log in to review and analyze your contracts</p>

        {showExpiredAlert && (
          <div className="alert alert-warning">
            Your session has expired. Please log in again.
          </div>
        )}

        {errorMsg && (
          <div className="alert alert-danger">
            {errorMsg}
          </div>
        )}

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
                  message: "Invalid email address",
                },
              })}
            />
            {errors.email && (
              <span className="error-msg-text">
                {errors.email.message}
              </span>
            )}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              className={`form-control ${errors.password ? "is-invalid" : ""}`}
              {...register("password", {
                required: "Password is required",
              })}
            />
            {errors.password && (
              <span className="error-msg-text">
                {errors.password.message}
              </span>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn btn-primary w-full mt-3"
          >
            {isSubmitting ? <div className="spinner spinner-sm" /> : "Log In"}
          </button>
        </form>

        <div className="auth-divider">
          <span>or</span>
        </div>

        <div className="google-btn-wrapper">
          <div id="google-signin-btn"></div>
        </div>

        <div className="auth-footer">
          Don't have an account?{" "}
          <Link to="/register">Create one free</Link>
        </div>
      </div>
    </div>
  );
};
