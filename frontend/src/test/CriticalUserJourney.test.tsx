import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { Routes, Route } from "react-router-dom";
import { Login } from "../pages/Login";
import { Security } from "../pages/Security";
import { UploadPage } from "../pages/UploadPage";
import { ContractDetailPage } from "../pages/ContractDetailPage";
import { QAPage } from "../pages/QAPage";
import { HistoryPage } from "../pages/HistoryPage";
import {
  renderWithProviders,
  mockUser,
  mockContract,
  mockAnalysisData,
  mockAuditLogItems,
} from "./test-utils";
import api from "../services/api";
import * as historyService from "../services/historyService";
import { useAuthStore } from "../store/useAuthStore";

vi.mock("../services/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("../services/historyService", () => ({
  fetchConversations: vi.fn().mockResolvedValue([]),
  fetchConversationDetail: vi.fn(),
  fetchActivityHistory: vi.fn(),
}));

// Polyfill URL.createObjectURL
window.URL.createObjectURL = vi.fn(() => "blob:mock-preview-url");

describe("Critical User Journey Integration Test (8-Step E2E Flow)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
  });

  it("executes the complete 8-step critical path from registration and 2FA to analysis, Q&A, and audit history", async () => {
    // ════════════════════════════════════════════════════════════════════════
    // STEP 1: Registration & Initial Authentication
    // ════════════════════════════════════════════════════════════════════════
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === "/auth/oauth-config") {
        return { data: { google_client_id: "test-client-id" } };
      }
      if (url === "/auth/me") {
        return { data: mockUser };
      }
      return { data: {} };
    });

    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        access_token: "jwt-token-step1",
        refresh_token: "refresh-token-step1",
        requires_2fa: false,
      },
    });

    const { unmount: unmountLogin1 } = renderWithProviders(<Login />);

    fireEvent.change(screen.getByPlaceholderText(/name@company.com/i), {
      target: { value: "lawyer@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/••••••••/i), {
      target: { value: "StrongPass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign In/i }));

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().user?.email).toBe("lawyer@example.com");
    });
    unmountLogin1();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 2: Enable Email 2FA in /security
    // ════════════════════════════════════════════════════════════════════════
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === "/auth/sessions") return { data: [] };
      if (url === "/users/me/retention") return { data: { retention_days: null } };
      return { data: {} };
    });

    vi.mocked(api.post).mockImplementation(async (url: string) => {
      if (url === "/auth/2fa/enable") {
        return { data: { message: "OTP sent to email" } };
      }
      if (url === "/auth/2fa/confirm") {
        return { data: { message: "2FA successfully enabled" } };
      }
      return { data: {} };
    });

    const { unmount: unmountSecurity } = renderWithProviders(<Security />);

    const enable2faBtn = await screen.findByRole("button", { name: /Enable Email 2FA/i });
    fireEvent.click(enable2faBtn);

    await waitFor(() => {
      expect(screen.getByText(/Verify Your Email/i)).toBeInTheDocument();
    });

    // Enter 6-digit OTP
    const otpInputs = screen.getAllByRole("textbox");
    expect(otpInputs.length).toBe(6);
    fireEvent.change(otpInputs[0], { target: { value: "123456" } });

    const verifyBtn = screen.getByRole("button", { name: /Verify & Activate/i });
    fireEvent.click(verifyBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/auth/2fa/confirm", {
        otp_code: "123456",
      });
      expect(useAuthStore.getState().user?.is_2fa_enabled).toBe(true);
    });
    unmountSecurity();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 3: Logout and Log In Through Full Email OTP Flow
    // ════════════════════════════════════════════════════════════════════════
    await useAuthStore.getState().logout();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);

    // Initial credentials submission triggers 2FA requirement
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        requires_2fa: true,
        pending_2fa_token: "pending-step3-token",
        message: "A 6-digit OTP has been sent to l***r@example.com",
      },
    });

    const { unmount: unmountLogin2 } = renderWithProviders(<Login />);

    fireEvent.change(screen.getByPlaceholderText(/name@company.com/i), {
      target: { value: "lawyer@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText(/••••••••/i), {
      target: { value: "StrongPass123!" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Sign In/i }));

    await waitFor(() => {
      expect(screen.getByText(/Two-Factor Authentication/i)).toBeInTheDocument();
      expect(screen.getByText(/A 6-digit OTP has been sent/i)).toBeInTheDocument();
    });

    // Verify OTP response
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        access_token: "jwt-token-step3-verified",
        refresh_token: "refresh-token-step3",
        requires_2fa: false,
      },
    });
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === "/auth/me") return { data: { ...mockUser, is_2fa_enabled: true } };
      return { data: { google_client_id: "test-client-id" } };
    });

    const loginOtpInputs = screen.getAllByRole("textbox");
    fireEvent.change(loginOtpInputs[0], { target: { value: "654321" } });

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().user?.is_2fa_enabled).toBe(true);
    });
    unmountLogin2();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 4: Upload a Contract & Ingest into Vault Storage
    // ════════════════════════════════════════════════════════════════════════
    vi.mocked(api.post).mockImplementation(async (url: string) => {
      if (url === "/contracts/upload") {
        return { data: { id: 42, filename: "Master_Services_Agreement.pdf" } };
      }
      if (url.includes("/extract")) return { data: { text: "Extracted legal text" } };
      if (url.includes("/chunk")) return { data: { chunks_count: 5 } };
      if (url.includes("/ingest")) return { data: { status: "success" } };
      return { data: {} };
    });

    const { unmount: unmountUpload } = renderWithProviders(<UploadPage />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const contractFile = new File(["mock contract pdf"], "Master_Services_Agreement.pdf", {
      type: "application/pdf",
    });
    Object.defineProperty(contractFile, "size", { value: 102400 });

    fireEvent.change(fileInput, { target: { files: [contractFile] } });

    const startIngestBtn = await screen.findByRole("button", { name: /Start Ingestion →/i });
    fireEvent.click(startIngestBtn);

    await waitFor(() => {
      expect(screen.getByText(/Document Ingested & Vectorized/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Open Analysis Workspace →/i })).toBeInTheDocument();
    });
    unmountUpload();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 5 & 6: Run Multi-Agent Analysis and View 3-Tier Risk Dialectic
    // ════════════════════════════════════════════════════════════════════════
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === "/contracts/42") return { data: mockContract };
      if (url === "/contracts/42/text") return { data: { text: "Extracted contract text" } };
      if (url === "/contracts/42/analysis") return { data: mockAnalysisData };
      return { data: {} };
    });

    const { unmount: unmountDetail } = renderWithProviders(
      <Routes>
        <Route path="/contracts/:id" element={<ContractDetailPage />} />
      </Routes>,
      { initialEntries: ["/contracts/42"] }
    );

    // Overview Tab
    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
      expect(screen.getByText(/Senior Partner Executive Synthesis/i)).toBeInTheDocument();
    });

    // Switch to 3-Tier Risk Dialectic
    const risksTab = screen.getByRole("button", { name: /3-Tier Risk Dialectic/i });
    fireEvent.click(risksTab);

    await waitFor(() => {
      // Certified RED, YELLOW, GREEN risk flags rendered
      expect(screen.getByText("Uncapped Consequential Damages Carve-Out")).toBeInTheDocument();
      expect(screen.getByText("Extended Non-Renewal Notice Period")).toBeInTheDocument();
      expect(screen.getByText("Standard Mutual Confidentiality Exceptions")).toBeInTheDocument();
    });
    unmountDetail();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 7: Ask Grounded Legal Question & Confirm Persistence Across Refresh
    // ════════════════════════════════════════════════════════════════════════
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        contract_id: 42,
        question: "Can I terminate this agreement early?",
        answer: "Section 7.2 permits termination for cause upon 30 days notice.",
        sources: [{ chunk_index: 1, text: "Section 7.2 Termination", section: "Section 7.2" }],
        conversation_id: 88,
      },
    });

    const { unmount: unmountQA1 } = renderWithProviders(
      <Routes>
        <Route path="/contracts/:id/ask" element={<QAPage />} />
      </Routes>,
      { initialEntries: ["/contracts/42/ask"] }
    );

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
    });

    const qaInput = screen.getByPlaceholderText(/Ask any legal question/i);
    fireEvent.change(qaInput, { target: { value: "Can I terminate this agreement early?" } });
    fireEvent.click(screen.getByTitle("Send query (Enter)"));

    await waitFor(() => {
      expect(
        screen.getByText(/Section 7\.2 permits termination for cause upon 30 days notice\./i)
      ).toBeInTheDocument();
    });
    unmountQA1();

    // Refresh simulation: reload page with conversation_id=88
    vi.mocked(historyService.fetchConversationDetail).mockResolvedValueOnce({
      id: 88,
      user_id: 1,
      contract_id: 42,
      title: "Termination Query",
      created_at: "2026-09-08T14:00:00Z",
      last_message_at: "2026-09-08T14:00:05Z",
      message_count: 2,
      messages: [
        {
          id: 1,
          conversation_id: 88,
          role: "user" as const,
          content: "Can I terminate this agreement early?",
          cited_clause_refs: [],
          created_at: "2026-09-08T14:00:01Z",
        },
        {
          id: 2,
          conversation_id: 88,
          role: "assistant" as const,
          content: "Section 7.2 permits termination for cause upon 30 days notice.",
          cited_clause_refs: [{ chunk_index: 1, text: "Section 7.2 Termination", section: "Section 7.2" }],
          created_at: "2026-09-08T14:00:05Z",
        },
      ],
    });

    const { unmount: unmountQA2 } = renderWithProviders(
      <Routes>
        <Route path="/contracts/:id/ask" element={<QAPage />} />
      </Routes>,
      { initialEntries: ["/contracts/42/ask?conversation_id=88"] }
    );

    await waitFor(() => {
      expect(screen.getByText("Can I terminate this agreement early?")).toBeInTheDocument();
      expect(
        screen.getByText(/Section 7\.2 permits termination for cause upon 30 days notice\./i)
      ).toBeInTheDocument();
    });
    unmountQA2();

    // ════════════════════════════════════════════════════════════════════════
    // STEP 8: Check History Page Shows All Prior Actions
    // ════════════════════════════════════════════════════════════════════════
    vi.mocked(historyService.fetchActivityHistory).mockResolvedValueOnce({
      items: mockAuditLogItems,
      total: mockAuditLogItems.length,
      limit: 25,
      offset: 0,
    });

    renderWithProviders(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByText("Activity Timeline & Governance")).toBeInTheDocument();
      expect(screen.getByText("Uploaded document Master_Services_Agreement.pdf")).toBeInTheDocument();
      expect(screen.getByText("Completed 5-agent LangGraph analysis for contract #42")).toBeInTheDocument();
      expect(screen.getByText("User logged in successfully via email/password")).toBeInTheDocument();
      expect(screen.getByText("Asked legal query: 'Can I terminate early?'")).toBeInTheDocument();
    });
    // This 8-step integration flow performs many sequential renders + waitFors;
    // give it headroom so it stays reliable under parallel CPU contention (incl. CI).
  }, 20000);
});
