import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { HistoryPage } from "../pages/HistoryPage";
import { renderWithProviders, mockUser, mockAuditLogItems } from "./test-utils";
import * as historyService from "../services/historyService";
import { useAuthStore } from "../store/useAuthStore";

vi.mock("../services/historyService", () => ({
  fetchActivityHistory: vi.fn(),
  fetchConversations: vi.fn().mockResolvedValue([]),
}));

describe("HistoryPage Component Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    useAuthStore.setState({
      user: mockUser,
      token: "mock-token",
      refreshToken: "mock-refresh",
      isAuthenticated: true,
      isLoading: false,
    });

    vi.mocked(historyService.fetchActivityHistory).mockResolvedValue({
      items: mockAuditLogItems,
      total: mockAuditLogItems.length,
      limit: 25,
      offset: 0,
    });
  });

  it("renders the activity timeline header and telemetry stat counters", async () => {
    renderWithProviders(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByText("Activity Timeline & Governance")).toBeInTheDocument();
      expect(screen.getByText("Total Events Recorded")).toBeInTheDocument();
      expect(screen.getByText("Auth & 2FA Sessions")).toBeInTheDocument();
      expect(screen.getByText("Document Ingestions")).toBeInTheDocument();
      expect(screen.getByText("AI Analyses Run")).toBeInTheDocument();
      expect(screen.getByText("4")).toBeInTheDocument();
    });
  });

  it("renders the list of audit log events with descriptions and action badges", async () => {
    renderWithProviders(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByText("Uploaded document Master_Services_Agreement.pdf")).toBeInTheDocument();
      expect(screen.getByText("Completed 5-agent LangGraph analysis for contract #42")).toBeInTheDocument();
      expect(screen.getByText("User logged in successfully via email/password")).toBeInTheDocument();
      expect(screen.getByText("Asked legal query: 'Can I terminate early?'")).toBeInTheDocument();
    });

    // Action tags
    expect(screen.getByText("UPLOAD_DOCUMENT")).toBeInTheDocument();
    expect(screen.getByText("RUN_ANALYSIS")).toBeInTheDocument();
  });

  it("filters displayed activity items when searching via quick search input", async () => {
    renderWithProviders(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByText("Uploaded document Master_Services_Agreement.pdf")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Search actions or documents\.\.\./i);
    fireEvent.change(searchInput, { target: { value: "LangGraph" } });

    // Matching item remains
    expect(screen.getByText("Completed 5-agent LangGraph analysis for contract #42")).toBeInTheDocument();

    // Non-matching items filtered out
    expect(screen.queryByText("Uploaded document Master_Services_Agreement.pdf")).not.toBeInTheDocument();
    expect(screen.queryByText("User logged in successfully via email/password")).not.toBeInTheDocument();
  });

  it("triggers category filter change when clicking category pills", async () => {
    renderWithProviders(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByText("All Events")).toBeInTheDocument();
    });

    const documentsPill = screen.getByRole("button", { name: "Documents" });
    fireEvent.click(documentsPill);

    await waitFor(() => {
      expect(historyService.fetchActivityHistory).toHaveBeenCalledWith(
        expect.objectContaining({
          category: "CONTRACTS",
        })
      );
    });
  });

  it("expands and collapses metadata details when payload toggle button is clicked", async () => {
    renderWithProviders(<HistoryPage />);

    await waitFor(() => {
      expect(screen.getByText("Uploaded document Master_Services_Agreement.pdf")).toBeInTheDocument();
    });

    // Find View Metadata buttons
    const payloadButtons = screen.getAllByRole("button", { name: /View Metadata/i });
    expect(payloadButtons.length).toBeGreaterThan(0);

    // Click to expand metadata
    fireEvent.click(payloadButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/102400/i)).toBeInTheDocument();
    });
  });
});
