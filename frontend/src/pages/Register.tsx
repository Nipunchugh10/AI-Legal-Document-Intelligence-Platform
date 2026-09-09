import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, Link } from "react-router-dom";
import api from "../services/api";
import { useAuthStore, type User } from "../store/useAuthStore";

declare global {
  interface Window {
    google?: any;
  }
}

interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
}

export const Register: React.FC = () => {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const login = useAuthStore((state) => state.login);

  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const handleGoogleCredentialResponse = async (response: any) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setIsSubmitting(true);

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
      navigate("/dashboard");
    } catch (err: any) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Google Sign-In failed. Please try again with email and password.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Initialize Google Sign-In SDK
  useEffect(() => {
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
            text: "signup_with",
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
  }, []);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<RegisterFormData>();

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard");
    }
  }, [isAuthenticated, navigate]);

  const passwordVal = watch("password") || "";
  const confirmPasswordVal = watch("confirmPassword") || "";

  // Password validation rules
  const hasMinLength = passwordVal.length >= 8;
  const hasUppercase = /[A-Z]/.test(passwordVal);
  const hasNumber = /[0-9]/.test(passwordVal);
  const hasSpecial = /[^A-Za-z0-9]/.test(passwordVal);

  const calculateStrength = () => {
    let score = 0;
    if (hasMinLength) score++;
    if (hasUppercase) score++;
    if (hasNumber) score++;
    if (hasSpecial) score++;
    return score;
  };

  const strengthScore = calculateStrength();
  const strengthLabels = ["Too Weak", "Weak", "Medium", "Strong", "Excellent"];
  const strengthColors = [
    "var(--color-text-dark)",
    "var(--color-danger)",
    "var(--color-warning)",
    "var(--color-accent)",
    "var(--color-success)",
  ];

  const onSubmit = async (data: RegisterFormData) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setIsSubmitting(true);

    try {
      // 1. Create user account
      await api.post("/auth/register", {
        email: data.email,
        password: data.password,
      });

      // 2. Perform auto-login immediately
      const loginRes = await api.post("/auth/login", {
        email: data.email,
        password: data.password,
      });

      const { access_token, refresh_token } = loginRes.data;

      localStorage.setItem("access_token", access_token);
      localStorage.setItem("refresh_token", refresh_token);

      const userResponse = await api.get<User>("/auth/me");
      const user = userResponse.data;

      login(access_token, refresh_token, user);
      setSuccessMsg("Account created successfully! Redirecting to your workspace...");

      setTimeout(() => {
        navigate("/dashboard");
      }, 1000);
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setErrorMsg(err.response.data.detail);
      } else {
        setErrorMsg("Failed to register. Please check your network connection.");
      }
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header className="navbar">
        <div onClick={() => navigate("/")} className="navbar-brand" style={{ cursor: "pointer" }}>
          Legal<span>Intelligence</span>
        </div>
      </header>

      <div className="auth-container" style={{ flex: 1 }}>
        <div className="glass-panel auth-card">
          <h2 className="auth-title">Create Account</h2>
          <p className="auth-subtitle">Get started with AI-driven contract intelligence</p>

          {successMsg && <div className="alert alert-success">{successMsg}</div>}
          {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}

          <form onSubmit={handleSubmit(onSubmit)}>
            {/* Email Field */}
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

            {/* Password Field */}
            <div className="form-group">
              <label className="form-label" htmlFor="password">
                Password
              </label>
              <div className="input-password-wrapper">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  className={`form-control ${errors.password ? "is-invalid" : ""}`}
                  {...register("password", {
                    required: "Password is required",
                    minLength: {
                      value: 8,
                      message: "Password must be at least 8 characters long",
                    },
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

              {/* Password Strength Meter Bar */}
              {passwordVal.length > 0 && (
                <div className="password-strength-container">
                  <div className="password-strength-header">
                    <span className="password-strength-label">Password Strength:</span>
                    <span
                      className="password-strength-value"
                      style={{ color: strengthColors[strengthScore] }}
                    >
                      {strengthLabels[strengthScore]}
                    </span>
                  </div>
                  <div className="password-strength-bar">
                    <div className={`password-strength-fill strength-${strengthScore}`} />
                  </div>

                  {/* Requirements Checklist */}
                  <div className="password-checklist">
                    <div className={`checklist-item ${hasMinLength ? "valid" : ""}`}>
                      <span>{hasMinLength ? "✓" : "○"}</span>
                      <span>8+ characters</span>
                    </div>
                    <div className={`checklist-item ${hasUppercase ? "valid" : ""}`}>
                      <span>{hasUppercase ? "✓" : "○"}</span>
                      <span>1 uppercase (A-Z)</span>
                    </div>
                    <div className={`checklist-item ${hasNumber ? "valid" : ""}`}>
                      <span>{hasNumber ? "✓" : "○"}</span>
                      <span>1 number (0-9)</span>
                    </div>
                    <div className={`checklist-item ${hasSpecial ? "valid" : ""}`}>
                      <span>{hasSpecial ? "✓" : "○"}</span>
                      <span>1 symbol (!@#$)</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password Field */}
            <div className="form-group">
              <label className="form-label" htmlFor="confirmPassword">
                Confirm Password
              </label>
              <div className="input-password-wrapper">
                <input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="••••••••"
                  className={`form-control ${errors.confirmPassword ? "is-invalid" : ""}`}
                  {...register("confirmPassword", {
                    required: "Please confirm your password",
                    validate: (value) =>
                      value === passwordVal ||
                      "Passwords do not match. Please verify that both password fields are identical.",
                  })}
                />
                <button
                  type="button"
                  className="btn-password-toggle"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  title={showConfirmPassword ? "Hide password" : "Show password"}
                  aria-label="Toggle confirm password visibility"
                >
                  {showConfirmPassword ? (
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
              {confirmPasswordVal.length > 0 &&
                confirmPasswordVal === passwordVal &&
                !errors.confirmPassword && (
                  <span style={{ fontSize: "0.78rem", color: "var(--color-success)", marginTop: "4px" }}>
                    ✓ Passwords match
                  </span>
                )}
              {errors.confirmPassword && (
                <span className="error-msg-text">{errors.confirmPassword.message}</span>
              )}
            </div>

            <button type="submit" disabled={isSubmitting} className="btn btn-primary w-full mt-3">
              {isSubmitting ? <div className="spinner spinner-sm" /> : "Create Free Account"}
            </button>
          </form>

          <div className="auth-divider">
            <span>or</span>
          </div>

          <div className="google-btn-wrapper">
            <div id="google-signin-btn"></div>
          </div>

          <div className="auth-footer">
            Already have an account? <Link to="/login">Sign In</Link>
          </div>
        </div>
      </div>
    </div>
  );
};
