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
  
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const login = useAuthStore((state) => state.login);

  const handleGoogleCredentialResponse = async (response: any) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setIsSubmitting(true);

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
            text: "signup_with",
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

  const passwordVal = watch("password");

  const onSubmit = async (data: RegisterFormData) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setIsSubmitting(true);

    try {
      await api.post("/auth/register", {
        email: data.email,
        password: data.password,
      });

      setSuccessMsg("Account created successfully! Redirecting to login...");
      
      // Redirect after 2 seconds
      setTimeout(() => {
        navigate("/login");
      }, 2000);
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
        <div
          onClick={() => navigate("/")}
          className="navbar-brand"
          style={{ cursor: "pointer" }}
        >
          Legal<span>Intelligence</span>
        </div>
      </header>
      <div className="auth-container" style={{ flex: 1 }}>
        <div className="glass-panel auth-card">
        <h2 className="auth-title">Create Account</h2>
        <p className="auth-subtitle">Get started with automated contract analysis</p>

        {successMsg && (
          <div className="alert alert-success">
            {successMsg}
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
                minLength: {
                  value: 8,
                  message: "Password must be at least 8 characters long",
                },
              })}
            />
            {errors.password && (
              <span className="error-msg-text">
                {errors.password.message}
              </span>
            )}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="confirmPassword">
              Confirm Password
            </label>
            <input
              id="confirmPassword"
              type="password"
              placeholder="••••••••"
              className={`form-control ${errors.confirmPassword ? "is-invalid" : ""}`}
              {...register("confirmPassword", {
                required: "Please confirm your password",
                validate: (value) =>
                  value === passwordVal || "Passwords do not match",
              })}
            />
            {errors.confirmPassword && (
              <span className="error-msg-text">
                {errors.confirmPassword.message}
              </span>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn btn-primary w-full mt-3"
          >
            {isSubmitting ? <div className="spinner spinner-sm" /> : "Register"}
          </button>
        </form>

        <div className="auth-divider">
          <span>or</span>
        </div>

        <div className="google-btn-wrapper">
          <div id="google-signin-btn"></div>
        </div>

        <div className="auth-footer">
          Already have an account?{" "}
          <Link to="/login">Sign In</Link>
        </div>
      </div>
    </div>
  </div>
  );
};
