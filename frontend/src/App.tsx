import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Welcome } from "./pages/Welcome";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { UploadPage } from "./pages/UploadPage";
import { ContractDetailPage } from "./pages/ContractDetailPage";
import { QAPage } from "./pages/QAPage";
import { ComparisonPage } from "./pages/ComparisonPage";
import { Security } from "./pages/Security";
import { HistoryPage } from "./pages/HistoryPage";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { useAuthStore } from "./store/useAuthStore";
import "./App.css";

import { ToastProvider } from "./context/ToastContext";

export const App: React.FC = () => {
  const checkAuth = useAuthStore((state) => state.checkAuth);

  // Initialize theme from localStorage and verify session on application mount
  useEffect(() => {
    checkAuth();
    const savedTheme = localStorage.getItem("theme") || "dark";
    if (savedTheme === "light") {
      document.documentElement.classList.add("light-theme");
    } else {
      document.documentElement.classList.remove("light-theme");
    }
  }, [checkAuth]);

  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<Welcome />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Protected App Shell Routes (Guarded by ProtectedRoute and wrapped in Layout) */}
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/contracts/upload" element={<UploadPage />} />
            <Route path="/contracts/:id" element={<ContractDetailPage />} />
            <Route path="/contracts/:id/ask" element={<QAPage />} />
            <Route path="/contracts/compare" element={<ComparisonPage />} />
            <Route path="/security" element={<Security />} />
            <Route path="/history" element={<HistoryPage />} />
          </Route>

          {/* Fallback Catch-All Route */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  );
};

export default App;
