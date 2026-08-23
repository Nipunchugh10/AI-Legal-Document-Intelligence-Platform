import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<{ id: number; name: string } | null>(null);

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
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = async (file: File) => {
    setUploadError(null);
    setUploadedFile(null);
    setUploadProgress(0);

    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!allowedExts.includes(ext)) {
      setUploadError(
        "Unsupported document format. Allowed: PDFs, Scans (PNG/JPG/WEBP/TIFF), Word (.docx), and Text files."
      );
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadError("Document size exceeds the 10MB limit.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true);

    try {
      const response = await api.post("/contracts/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadProgress(percentCompleted);
          }
        },
      });

      setUploadedFile({ id: response.data.id, name: response.data.filename });
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setUploadError(err.response.data.detail);
      } else {
        setUploadError("Failed to upload document. Please try again.");
      }
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="placeholder-view-container">
      {/* Hero Header */}
      <div className="placeholder-hero-card">
        <div className="placeholder-badge">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          Multimodal Ingestion Engine
        </div>
        <h1 className="placeholder-title">Upload Legal Document</h1>
        <p className="placeholder-desc">
          Upload any contract, NDA, lease, or legal agreement. Our engine ingests digital PDFs,
          scanned documents, smartphone photos via Gemini Vision OCR, and Word documents.
        </p>

        {uploadError && <div className="alert alert-danger">{uploadError}</div>}

        {uploadedFile && (
          <div className="alert alert-success">
            <div>
              <strong>Document Uploaded Successfully:</strong> {uploadedFile.name}
            </div>
            <div style={{ marginTop: "10px", display: "flex", gap: "10px" }}>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => navigate(`/contracts/${uploadedFile.id}`)}
              >
                Open Contract Workspace
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => navigate("/dashboard")}
              >
                Go to Vault
              </button>
            </div>
          </div>
        )}

        {/* Drag and Drop Zone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{
            border: isDragging ? "2px dashed var(--color-primary)" : "2px dashed var(--color-border)",
            borderRadius: "16px",
            padding: "48px 24px",
            textAlign: "center",
            background: isDragging ? "rgba(92, 98, 236, 0.08)" : "rgba(255, 255, 255, 0.02)",
            cursor: "pointer",
            transition: "all 0.2s ease",
            marginTop: "10px",
          }}
          onClick={() => document.getElementById("file-upload-input")?.click()}
        >
          <input
            type="file"
            id="file-upload-input"
            style={{ display: "none" }}
            onChange={handleFileInput}
            accept=".pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg,.webp,.tiff,.bmp"
          />

          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "50%",
              background: "rgba(92, 98, 236, 0.12)",
              color: "var(--color-primary)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px auto",
            }}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="28"
              height="28"
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

          <h3 style={{ fontSize: "1.2rem", fontWeight: "600", marginBottom: "8px" }}>
            {isUploading ? "Uploading & Indexing Document..." : "Click or Drag & Drop Document Here"}
          </h3>
          <p style={{ fontSize: "0.88rem", color: "var(--color-text-muted)" }}>
            Supports PDF, DOCX, TXT, and Smartphone Photos/Scans (PNG, JPG, WEBP) up to 10MB
          </p>

          {isUploading && (
            <div style={{ marginTop: "20px", maxWidth: "360px", margin: "20px auto 0" }}>
              <div
                style={{
                  height: "6px",
                  background: "rgba(255, 255, 255, 0.1)",
                  borderRadius: "4px",
                  overflow: "hidden",
                }}
              >
                <div
                  style={{
                    height: "100%",
                    width: `${uploadProgress}%`,
                    background: "linear-gradient(90deg, var(--color-primary), var(--color-secondary))",
                    transition: "width 0.3s ease",
                  }}
                />
              </div>
              <span style={{ fontSize: "0.78rem", color: "var(--color-text-muted)", marginTop: "6px", display: "inline-block" }}>
                {uploadProgress}% Uploaded
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
