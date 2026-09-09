import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { Routes, Route } from "react-router-dom";
import { QAPage } from "../pages/QAPage";
import { renderWithProviders, mockContract } from "./test-utils";
import api from "../services/api";
import * as historyService from "../services/historyService";

vi.mock("../services/api", () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
    },
  };
});

vi.mock("../services/historyService", () => ({
  fetchConversations: vi.fn().mockResolvedValue([]),
  fetchConversationDetail: vi.fn().mockResolvedValue({ id: 1, contract_id: 42, title: "Test", created_at: "2026-09-08T00:00:00Z", messages: [] }),
}));

const renderQAPage = (initialEntry = "/contracts/42/ask") =>
  renderWithProviders(
    <Routes>
      <Route path="/contracts/:id/ask" element={<QAPage />} />
    </Routes>,
    { initialEntries: [initialEntry] }
  );

describe("QAPage Component Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === "/contracts/42") {
        return { data: mockContract };
      }
      if (url === "/contracts/42/text") {
        return { data: { text: "Section 7.2: Termination for cause with 30 days notice." } };
      }
      return { data: {} };
    });
  });

  it("renders the chat header, suggested questions, and query input textarea", async () => {
    renderQAPage();

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
    });

    expect(screen.getByPlaceholderText(/Ask any legal question/i)).toBeInTheDocument();
    expect(screen.getByText(/Early Termination/i)).toBeInTheDocument();
    expect(screen.getByText(/Liability & Indemnity/i)).toBeInTheDocument();
  });

  it("sends a message, appends user message to chat, and renders assistant response with sources", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        contract_id: 42,
        question: "Can I terminate this agreement early?",
        answer: "Yes, under Section 7.2 either party may terminate for material breach with thirty (30) days written notice.",
        sources: [
          {
            chunk_index: 2,
            text: "Either party may terminate for material breach with thirty (30) days written notice.",
            section: "Section 7.2",
            page: 3,
            similarity: 0.89,
          },
        ],
        conversation_id: 101,
      },
    });

    renderQAPage();

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Ask any legal question/i);
    fireEvent.change(textarea, { target: { value: "Can I terminate this agreement early?" } });

    const sendBtn = screen.getByTitle("Send query (Enter)");
    expect(sendBtn).not.toBeDisabled();
    fireEvent.click(sendBtn);

    // User message should appear immediately
    expect(screen.getByText("Can I terminate this agreement early?")).toBeInTheDocument();

    // Assistant response and citation should appear after API resolves
    await waitFor(() => {
      expect(
        screen.getByText(/Yes, under Section 7\.2 either party may terminate for material breach/i)
      ).toBeInTheDocument();
      expect(screen.getAllByText(/Section 7\.2/i)[0]).toBeInTheDocument();
    });
  });

  it("sends a pre-canned suggested question when clicked", async () => {
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        contract_id: 42,
        question: "Can I terminate this contract early? What notice period and exit penalties apply?",
        answer: "Section 7.2 requires 30 days written notice with no exit penalties.",
        sources: [],
        conversation_id: 102,
      },
    });

    renderQAPage();

    await waitFor(() => {
      expect(screen.getByText(/Early Termination/i)).toBeInTheDocument();
    });

    const earlyTermBtn = screen.getByText(/Early Termination/i).closest("button");
    expect(earlyTermBtn).toBeTruthy();
    fireEvent.click(earlyTermBtn!);

    await waitFor(() => {
      expect(
        screen.getByText(/Section 7\.2 requires 30 days written notice with no exit penalties\./i)
      ).toBeInTheDocument();
    });
  });

  it("persists conversation across refresh by loading existing thread messages", async () => {
    vi.mocked(historyService.fetchConversationDetail).mockResolvedValueOnce({
      id: 55,
      user_id: 1,
      contract_id: 42,
      title: "Early Termination Discussion",
      created_at: "2026-09-08T12:00:00Z",
      last_message_at: "2026-09-08T12:00:05Z",
      message_count: 2,
      messages: [
        {
          id: 1,
          conversation_id: 55,
          role: "user" as const,
          content: "What is the non-renewal notice period?",
          cited_clause_refs: [],
          created_at: "2026-09-08T12:00:01Z",
        },
        {
          id: 2,
          conversation_id: 55,
          role: "assistant" as const,
          content: "The non-renewal notice window is 90 days prior to term expiration.",
          cited_clause_refs: [
            { chunk_index: 5, text: "Notice must be given 90 days before expiration.", section: "Section 8.1" },
          ],
          created_at: "2026-09-08T12:00:05Z",
        },
      ],
    });

    renderQAPage("/contracts/42/ask?conversation_id=55");

    await waitFor(() => {
      expect(historyService.fetchConversationDetail).toHaveBeenCalledWith(55);
      expect(screen.getByText("What is the non-renewal notice period?")).toBeInTheDocument();
      expect(
        screen.getByText("The non-renewal notice window is 90 days prior to term expiration.")
      ).toBeInTheDocument();
    });
  });

  it("displays error message if contract analysis is required prior to Q&A", async () => {
    vi.mocked(api.post).mockRejectedValueOnce({
      response: {
        status: 400,
        data: {
          detail: "Contract must be analyzed before asking questions.",
        },
      },
    });

    renderQAPage();

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Ask any legal question/i);
    fireEvent.change(textarea, { target: { value: "Who is party A?" } });

    const sendBtn = screen.getByTitle("Send query (Enter)");
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/Contract must be analyzed before asking questions\./i)
      ).toBeInTheDocument();
    });
  });
});
