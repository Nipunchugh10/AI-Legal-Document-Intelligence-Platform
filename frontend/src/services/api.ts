import axios from "axios";

// Base URL for backend API. Can be overridden by environment variable VITE_API_URL.
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor to attach JWT token to all outgoing requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth failures and refresh access tokens
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Check if error is 401 and it's not a retry (to prevent infinite loop) and not a login request
    if (
      error.response &&
      error.response.status === 401 &&
      !originalRequest._retry &&
      originalRequest.url !== "/auth/login"
    ) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");

      // If the error response specifies "SESSION_EXPIRED", don't attempt to refresh
      const isSessionExpired = error.response.data?.detail === "SESSION_EXPIRED";

      if (refreshToken && !isSessionExpired) {
        try {
          // Attempt to refresh the access token using the refresh token
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token: new_refresh_token } = response.data;

          // Store new tokens
          localStorage.setItem("access_token", access_token);
          localStorage.setItem("refresh_token", new_refresh_token);

          // Retry the original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return axios(originalRequest);
        } catch (refreshError) {
          // If refresh fails, clean up and redirect to login
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login?expired=true";
          return Promise.reject(refreshError);
        }
      } else {
        // No refresh token or session has explicitly expired
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");

        const currentPath = window.location.pathname;
        if (currentPath !== "/login" && currentPath !== "/register") {
          window.location.href = "/login?expired=true";
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
