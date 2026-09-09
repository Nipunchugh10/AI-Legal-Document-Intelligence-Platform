import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { Routes, Route } from "react-router-dom";
import { ContractDetailPage } from "../pages/ContractDetailPage";
import { renderWithProviders, mockContract, mockAnalysisData } from "./test-utils";
import api from "../services/api";

vi.mock("../services/api", () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
    },
  };
});

// Mock historyService
vi.mock("../services/historyService", () => ({
  fetchConversations: vi.fn().mockResolvedValue([]),
}));

const renderDetailPage = () =>
  renderWithProviders(
    <Routes>
      <Route path="/contracts/:id" element={<ContractDetailPage />} />
    </Routes>,
    { initialEntries: ["/contracts/42"] }
  );

describe("ContractDetailPage Component Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === "/contracts/42") {
        return { data: mockContract };
      }
      if (url === "/contracts/42/text") {
        return { data: { text: "Full extracted legal text of Master Services Agreement..." } };
      }
      if (url === "/contracts/42/analysis") {
        return { data: mockAnalysisData };
      }
      return { data: {} };
    });
  });

  it("renders contract header, status badge, and executive overview tab by default", async () => {
    renderDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
      expect(screen.getByText(/ANALYZED/i)).toBeInTheDocument();
    });

    // Executive overview elements
    expect(screen.getByText(/Senior Partner Executive Synthesis/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Comprehensive SaaS agreement between Acme Cloud Solutions and Global Enterprises/i)
    ).toBeInTheDocument();

    // Metadata items in overview
    expect(screen.getByText("Acme Cloud Solutions Inc.")).toBeInTheDocument();
    expect(screen.getByText("Global Enterprises LLC")).toBeInTheDocument();
    expect(screen.getByText("State of California")).toBeInTheDocument();
  });

  it("switches to the 3-Tier Risk Dialectic tab and renders risk cards", async () => {
    renderDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
    });

    const risksTab = screen.getByRole("button", { name: /3-Tier Risk Dialectic/i });
    fireEvent.click(risksTab);

    await waitFor(() => {
      expect(screen.getByText("Uncapped Consequential Damages Carve-Out")).toBeInTheDocument();
      expect(screen.getByText("Extended Non-Renewal Notice Period")).toBeInTheDocument();
      expect(screen.getByText("Standard Mutual Confidentiality Exceptions")).toBeInTheDocument();
    });

    // Verify RED_FLAG IRAC issue and verbatim clause text
    expect(screen.getByText("Is indemnity exposure uncapped?")).toBeInTheDocument();
    expect(
      screen.getByText(/The liability cap shall not apply to indemnification obligations under Section 10\./i)
    ).toBeInTheDocument();
  });

  it("filters risks by severity pill when clicked in the risks tab", async () => {
    renderDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
    });

    const risksTab = screen.getByRole("button", { name: /3-Tier Risk Dialectic/i });
    fireEvent.click(risksTab);

    await waitFor(() => {
      expect(screen.getByText("Uncapped Consequential Damages Carve-Out")).toBeInTheDocument();
    });

    // Click the Critical Red pill filter
    const redFilterBtn = screen.getByRole("button", { name: /Critical Red/i });
    fireEvent.click(redFilterBtn);

    // Red flag should be visible, Yellow flag should be hidden
    expect(screen.getByText("Uncapped Consequential Damages Carve-Out")).toBeInTheDocument();
    expect(screen.queryByText("Extended Non-Renewal Notice Period")).not.toBeInTheDocument();
  });

  it("switches to 8-Domain Compliance tab and renders statutory findings", async () => {
    renderDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
    });

    const complianceTab = screen.getByRole("button", { name: /8-Domain Compliance/i });
    fireEvent.click(complianceTab);

    await waitFor(() => {
      expect(screen.getByText("DPDP Act 2023")).toBeInTheDocument();
      expect(
        screen.getByText(/The agreement processes Indian user data but fails to specify the contact details/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/Insert DPO name, official email address, and grievance redressal timeline/i)
      ).toBeInTheDocument();
    });
  });

  it("switches to Key Clauses tab and displays extracted 9-point checklist clauses", async () => {
    renderDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
    });

    const clausesTab = screen.getByRole("button", { name: /Key Clauses/i });
    fireEvent.click(clausesTab);

    await waitFor(() => {
      expect(screen.getByText(/payment terms/i)).toBeInTheDocument();
      expect(screen.getByText(/Customer shall pay invoices within thirty \(30\) days of receipt\./i)).toBeInTheDocument();
      expect(screen.getByText(/termination clauses/i)).toBeInTheDocument();
      expect(screen.getByText(/Section 7\.2/i)).toBeInTheDocument();
    });
  });

  it("switches to Document Text tab and displays extracted contract text", async () => {
    renderDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText("Master_Services_Agreement.pdf")[0]).toBeInTheDocument();
    });

    const textTab = screen.getByRole("button", { name: /Document Text/i });
    fireEvent.click(textTab);

    await waitFor(() => {
      expect(
        screen.getByText(/Full extracted legal text of Master Services Agreement\.\.\./i)
      ).toBeInTheDocument();
    });
  });
});
