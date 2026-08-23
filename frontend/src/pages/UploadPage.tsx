import React, { useState, useRef } from "react";
import { useNavigate, Link } from "react-router-dom";
import api from "../services/api";
import "./UploadPage.css";

interface IngestionStep {
  id: number;
  label: string;
  description: string;
  status: "idle" | "in-progress" | "completed" | "failed";
}

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Pipeline execution state
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedContractId, setUploadedContractId] = useState<number | null>(null);
  const [completedContractName, setCompletedContractName] = useState<string | null>(null);

  const [steps, setSteps] = useState<IngestionStep[]>([
    {
      id: 1,
      label: "Upload & File Registration",
      description: "Validating format and storing raw document in encrypted vault storage.",
      status: "idle",
    },
    {
      id: 2,
      label: "Text Extraction & Vision OCR",
      description: "Extracting legal text structures, OCR scanning, and page layouts.",
      status: "idle",
    },
    {
      id: 3,
      label: "Token Chunking & Vector Embeddings",
      description: "Creating sliding context chunks and indexing into ChromaDB vector store.",
      status: "idle",
    },
  ]);

  const allowedExts = [
    ".pdf",
    ".docx",
    ".doc",
    ".txt",
    ".md",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".tiff",
    ".bmp",
  ];

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSelectFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSelectFile(e.target.files[0]);
    }
  };

  const validateAndSelectFile = (file: File) => {
    setUploadError(null);
    setUploadedContractId(null);
    setCompletedContractName(null);

    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowedExts.includes(ext)) {
      setUploadError(
        "Unsupported document format. Allowed: PDFs, Scans (PNG/JPG/WEBP), Word (.docx), and Text files."
      );
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadError("Document size exceeds the 10MB limit.");
      return;
    }

    setSelectedFile(file);

    // Create thumbnail preview if image
    if (file.type.startsWith("image/")) {
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    } else {
      setPreviewUrl(null);
    }

    // Reset steps
    setSteps([
      {
        id: 1,
        label: "Upload & File Registration",
        description: "Validating format and storing raw document in encrypted vault storage.",
        status: "idle",
      },
      {
        id: 2,
        label: "Text Extraction & Vision OCR",
        description: "Extracting legal text structures, OCR scanning, and page layouts.",
        status: "idle",
      },
      {
        id: 3,
        label: "Token Chunking & Vector Embeddings",
        description: "Creating sliding context chunks and indexing into ChromaDB vector store.",
        status: "idle",
      },
    ]);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getDocTypeTag = (fileName: string) => {
    const ext = fileName.split(".").pop()?.toLowerCase();
    if (ext === "pdf") return "PDF Document";
    if (ext === "docx" || ext === "doc") return "Word Agreement";
    if (["png", "jpg", "jpeg", "webp"].includes(ext || "")) return "Photo Scan / OCR";
    return "Plain Text / Markdown";
  };

  // Run full automated ingestion pipeline
  const runIngestionPipeline = async () => {
    if (!selectedFile) return;

    setUploadError(null);
    setIsProcessing(true);

    try {
      // ── Step 1: Upload ───────────────────────────────────────────────────
      updateStepStatus(0, "in-progress");
      const formData = new FormData();
      formData.append("file", selectedFile);

      const uploadRes = await api.post("/contracts/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const contractId = uploadRes.data.id;
      setUploadedContractId(contractId);
      setCompletedContractName(uploadRes.data.filename);
      updateStepStatus(0, "completed");

      // ── Step 2: Text Extraction ──────────────────────────────────────────
      updateStepStatus(1, "in-progress");
      await api.post(`/contracts/${contractId}/extract`);
      updateStepStatus(1, "completed");

      // ── Step 3: Chunking & Vector Ingestion ──────────────────────────────
      updateStepStatus(2, "in-progress");
      await api.post(`/contracts/${contractId}/chunk`);
      await api.post(`/contracts/${contractId}/ingest?background=false`);
      updateStepStatus(2, "completed");

      setIsProcessing(false);
    } catch (err: any) {
      setIsProcessing(false);
      const activeIdx = steps.findIndex((s) => s.status === "in-progress");
      if (activeIdx !== -1) {
        updateStepStatus(activeIdx, "failed");
      }
      if (err.response?.data?.detail) {
        setUploadError(err.response.data.detail);
      } else {
        setUploadError("An error occurred during ingestion. Please try again.");
      }
    }
  };

  const updateStepStatus = (
    stepIdx: number,
    status: "idle" | "in-progress" | "completed" | "failed"
  ) => {
    setSteps((prev) =>
      prev.map((step, idx) => (idx === stepIdx ? { ...step, status } : step))
    );
  };

  const resetAll = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setUploadError(null);
    setUploadedContractId(null);
    setCompletedContractName(null);
    setIsProcessing(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="upload-page-container">
      {/* Top Header */}
      <section className="upload-header-row">
        <div className="upload-title-group">
          <h1>Document Ingestion Workspace</h1>
          <p>
            Upload legal agreements for automated parsing, OCR extraction, token chunking, and
            vector store indexing.
          </p>
        </div>
        <Link to="/dashboard" className="btn btn-secondary">
          ← Back to Vault
        </Link>
      </section>

      {/* 2-Column Grid */}
      <div className="upload-layout-grid">
        {/* Main Left Ingestion Panel */}
        <div className="dropzone-main-panel">
          {uploadError && (
            <div className="alert alert-danger">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{uploadError}</span>
            </div>
          )}

          {/* Success State */}
          {uploadedContractId && steps.every((s) => s.status === "completed") ? (
            <div className="upload-success-panel">
              <div className="upload-success-icon">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="28"
                  height="28"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <h3>Document Ingested & Vectorized</h3>
              <p>
                <strong>"{completedContractName}"</strong> is now fully indexed with 384-dimensional
                embeddings and ready for multi-agent IRAC analysis.
              </p>

              <div className="upload-success-actions">
                <button
                  className="btn btn-primary"
                  onClick={() => navigate(`/contracts/${uploadedContractId}`)}
                >
                  Open Analysis Workspace →
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => navigate(`/contracts/${uploadedContractId}/ask`)}
                >
                  Ask Grounded Q&A
                </button>
                <button className="btn btn-secondary" onClick={resetAll}>
                  Upload Another Document
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Dropzone */}
              <div
                className={`multimodal-dropzone ${isDragging ? "is-dragging" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => !isProcessing && fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  style={{ display: "none" }}
                  onChange={handleFileInput}
                  accept=".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.webp,.tiff,.bmp"
                  disabled={isProcessing}
                />

                <div className="dropzone-icon-circle">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="30"
                    height="30"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                </div>

                <div className="dropzone-primary-text">
                  {isDragging
                    ? "Release file to upload"
                    : selectedFile
                    ? "Replace Selected Document"
                    : "Drag and drop your contract here"}
                </div>
                <div className="dropzone-secondary-text">
                  Supports digital PDFs, camera photo scans, Word agreements, and plain text up to
                  10MB.
                </div>

                <div className="format-badges-row">
                  <span className="format-badge">PDF</span>
                  <span className="format-badge">DOCX</span>
                  <span className="format-badge">PNG / JPG</span>
                  <span className="format-badge">WEBP</span>
                  <span className="format-badge">TXT / MD</span>
                </div>
              </div>

              {/* Selected File Card */}
              {selectedFile && (
                <div className="selected-file-card">
                  <div className="selected-file-info">
                    <div className="file-thumbnail-box">
                      {previewUrl ? (
                        <img src={previewUrl} alt="Thumbnail" className="file-thumbnail-img" />
                      ) : (
                        <span>{selectedFile.name.split(".").pop()?.toUpperCase()}</span>
                      )}
                    </div>
                    <div className="selected-file-details">
                      <span className="selected-file-name">{selectedFile.name}</span>
                      <span className="selected-file-meta">
                        {formatFileSize(selectedFile.size)} • {getDocTypeTag(selectedFile.name)}
                      </span>
                    </div>
                  </div>

                  {!isProcessing && (
                    <div style={{ display: "flex", gap: "8px" }}>
                      <button className="btn btn-secondary btn-sm" onClick={resetAll}>
                        Clear
                      </button>
                      <button className="btn btn-primary btn-sm" onClick={runIngestionPipeline}>
                        Start Ingestion →
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Ingestion Stepper Pipeline */}
              {isProcessing && (
                <div className="pipeline-stepper">
                  <div className="pipeline-stepper-title">
                    <span>Automated Ingestion Pipeline</span>
                    <div className="spinner spinner-sm" />
                  </div>

                  <div className="pipeline-steps-list">
                    {steps.map((step) => (
                      <div
                        key={step.id}
                        className={`pipeline-step-item ${step.status}`}
                      >
                        <div className="step-indicator-circle">
                          {step.status === "completed" ? (
                            "✓"
                          ) : step.status === "in-progress" ? (
                            <div className="spinner spinner-xs" />
                          ) : (
                            step.id
                          )}
                        </div>
                        <div>
                          <div>{step.label}</div>
                          <div style={{ fontSize: "0.76rem", color: "var(--color-text-dark)", marginTop: "2px" }}>
                            {step.description}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Right Information & Guide Sidebar */}
        <div className="upload-sidebar-card">
          <div className="sidebar-section-title">Multimodal Ingestion Capabilities</div>

          <div className="capability-feature-list">
            <div className="capability-feature-item">
              <div className="capability-feature-icon">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <div className="capability-feature-text">
                <h4>Native & Scanned PDFs</h4>
                <p>PyMuPDF extractor with fallback to pdfplumber for complex multi-column tables.</p>
              </div>
            </div>

            <div className="capability-feature-item">
              <div className="capability-feature-icon">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                  <circle cx="9" cy="9" r="2" />
                  <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
                </svg>
              </div>
              <div className="capability-feature-text">
                <h4>Gemini Vision OCR</h4>
                <p>Processes smartphone photos and physical document scans with multi-angle correction.</p>
              </div>
            </div>

            <div className="capability-feature-item">
              <div className="capability-feature-icon">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
              </div>
              <div className="capability-feature-text">
                <h4>Word Documents (.docx)</h4>
                <p>Extracts formatted text, nested clauses, annexures, and execution blocks.</p>
              </div>
            </div>

            <div className="capability-feature-item">
              <div className="capability-feature-icon">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <div className="capability-feature-text">
                <h4>8-Domain Benchmark</h4>
                <p>Automatically prepares context for Real Estate, Corporate, SaaS, Labour, and Trade acts.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
