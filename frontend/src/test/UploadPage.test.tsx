import { describe, it, expect, vi, beforeEach } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import { UploadPage } from "../pages/UploadPage";
import { renderWithProviders } from "./test-utils";
import api from "../services/api";

// Mock the API module
vi.mock("../services/api", () => {
  return {
    default: {
      get: vi.fn(),
      post: vi.fn(),
    },
  };
});

// Polyfill URL.createObjectURL
window.URL.createObjectURL = vi.fn(() => "blob:mock-preview-url");

describe("UploadPage Component Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the upload dropzone and format hints", () => {
    renderWithProviders(<UploadPage />);

    expect(screen.getByText(/Drag and drop your contract here/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Supports digital PDFs, camera photo scans, Word agreements, and plain text up to 10MB/i)
    ).toBeInTheDocument();
  });

  it("rejects files with unsupported formats and displays an error message", async () => {
    renderWithProviders(<UploadPage />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();

    const invalidFile = new File(["malicious binary content"], "virus.exe", {
      type: "application/x-msdownload",
    });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    await waitFor(() => {
      expect(
        screen.getByText(/Unsupported document format. Allowed: PDFs, Scans \(PNG\/JPG\/WEBP\), Word \(\.docx\), and Text files./i)
      ).toBeInTheDocument();
    });
  });

  it("rejects files exceeding the 10MB size limit", async () => {
    renderWithProviders(<UploadPage />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();

    // Create a 15MB mock file
    const largeFile = new File(["x".repeat(100)], "huge_contract.pdf", {
      type: "application/pdf",
    });
    Object.defineProperty(largeFile, "size", { value: 15 * 1024 * 1024 });

    fireEvent.change(fileInput, { target: { files: [largeFile] } });

    await waitFor(() => {
      expect(
        screen.getByText(/Document size exceeds the 10MB limit./i)
      ).toBeInTheDocument();
    });
  });

  it("accepts valid PDF files and displays file metadata with ingestion pipeline button", async () => {
    renderWithProviders(<UploadPage />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(["%PDF-1.4 mock content"], "Consulting_Agreement.pdf", {
      type: "application/pdf",
    });
    Object.defineProperty(validFile, "size", { value: 512 * 1024 }); // 512 KB

    fireEvent.change(fileInput, { target: { files: [validFile] } });

    await waitFor(() => {
      expect(screen.getByText("Consulting_Agreement.pdf")).toBeInTheDocument();
      expect(screen.getByText(/PDF Document/i)).toBeInTheDocument();
      expect(screen.getByText(/512.0 KB/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Start Ingestion →/i })).toBeInTheDocument();
    });
  });

  it("runs the full automated ingestion pipeline on click and transitions to success state", async () => {
    vi.mocked(api.post).mockImplementation(async (url: string) => {
      if (url === "/contracts/upload") {
        return { data: { id: 88, filename: "Consulting_Agreement.pdf" } };
      }
      if (url.includes("/extract")) {
        return { data: { text: "extracted text" } };
      }
      if (url.includes("/chunk")) {
        return { data: { chunks_count: 5 } };
      }
      if (url.includes("/ingest")) {
        return { data: { status: "success" } };
      }
      return { data: {} };
    });

    renderWithProviders(<UploadPage />);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(["%PDF-1.4 content"], "Consulting_Agreement.pdf", {
      type: "application/pdf",
    });
    Object.defineProperty(validFile, "size", { value: 256 * 1024 });

    fireEvent.change(fileInput, { target: { files: [validFile] } });

    const startBtn = await screen.findByRole("button", { name: /Start Ingestion →/i });
    fireEvent.click(startBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/contracts/upload", expect.any(FormData), expect.any(Object));
      expect(api.post).toHaveBeenCalledWith("/contracts/88/extract");
      expect(api.post).toHaveBeenCalledWith("/contracts/88/chunk");
      expect(api.post).toHaveBeenCalledWith("/contracts/88/ingest?background=false");
    });

    await waitFor(() => {
      expect(screen.getByText(/Document Ingested & Vectorized/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Open Analysis Workspace →/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Ask Grounded Q&A/i })).toBeInTheDocument();
    });
  });

  it("handles drop events on the dropzone area", async () => {
    renderWithProviders(<UploadPage />);

    const dropArea = screen.getByText(/Drag and drop your contract here/i).closest("div");
    expect(dropArea).toBeInTheDocument();

    const file = new File(["sample agreement"], "Lease_Contract.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    Object.defineProperty(file, "size", { value: 100 * 1024 });

    fireEvent.drop(dropArea!, {
      dataTransfer: {
        files: [file],
      },
    });

    await waitFor(() => {
      expect(screen.getByText("Lease_Contract.docx")).toBeInTheDocument();
      expect(screen.getByText(/100\.0 KB/i)).toBeInTheDocument();
    });
  });
});
