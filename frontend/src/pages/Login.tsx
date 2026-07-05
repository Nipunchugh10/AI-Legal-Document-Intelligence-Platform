import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import api from "../services/api";
import { useAuthStore, type User } from "../store/useAuthStore";

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
      
      const { access_token, refresh_token } = response.data;

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
              className="form-control"
              style={{ borderColor: errors.email ? "var(--color-danger)" : "" }}
              {...register("email", {
                required: "Email is required",
                pattern: {
                  value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                  message: "Invalid email address",
                },
              })}
            />
            {errors.email && (
              <span style={{ color: "var(--color-danger)", fontSize: "0.8rem", fontWeight: 500 }}>
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
              className="form-control"
              style={{ borderColor: errors.password ? "var(--color-danger)" : "" }}
              {...register("password", {
                required: "Password is required",
              })}
            />
            {errors.password && (
              <span style={{ color: "var(--color-danger)", fontSize: "0.8rem", fontWeight: 500 }}>
                {errors.password.message}
              </span>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn btn-primary"
            style={{ width: "100%", marginTop: "12px" }}
          >
            {isSubmitting ? <div className="spinner" style={{ width: "18px", height: "18px" }} /> : "Log In"}
          </button>
        </form>

        <div className="auth-footer">
          Don't have an account?{" "}
          <Link to="/register">Create one free</Link>
        </div>
      </div>
    </div>
  );
};
