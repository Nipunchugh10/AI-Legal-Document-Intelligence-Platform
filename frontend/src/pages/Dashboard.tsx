import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";
import { useContractStore, type Contract } from "../store/useContractStore";

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const contracts = useContractStore((state) => state.contracts);
  const setContracts = useContractStore((state) => state.setContracts);
  const removeContract = useContractStore((state) => state.removeContract);
  const searchQuery = useContractStore((state) => state.searchQuery);

  const [isLoading, setIsLoading] = useState(true);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // Fetch contracts on load
  const fetchContracts = async () => {
    setIsLoading(true);
    try {
      const response = await api.get<Contract[]>("/contracts/");
      setContracts(response.data);
    } catch (err) {
      console.error("Failed to load contracts:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchContracts();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    setUploadError(null);
    setUploadSuccess(false);
    setIsUploading(true);

    // Client-side validations
    const allowedExts = [
      ".pdf",
      ".png",
      ".jpg",
      ".jpeg",
      ".webp",
      ".tiff",
      ".bmp",
      ".docx",
      ".doc",
      ".txt",
      ".md",
      ".rtf",
    ];
    const fileExt = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();

    if (!allowedExts.includes(fileExt)) {
      setUploadError(
        "Unsupported file type. Allowed: PDF, Photo Scans (PNG, JPG, WEBP), Word (.docx), and Text (.txt)."
      );
      setIsUploading(false);
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadError("File size exceeds 10MB limit.");
      setIsUploading(false);
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      await api.post("/contracts/upload", formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      setUploadSuccess(true);
      fetchContracts(); // refresh list
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setUploadError(err.response.data.detail);
      } else {
        setUploadError("An error occurred during file upload.");
      }
    } finally {
      setIsUploading(false);
      e.target.value = "";
    }
  };

  const handleDeleteContract = async (contractId: number) => {
    if (
      !window.confirm(
        "Are you sure you want to delete this contract? This will permanently remove the contract, all analyses, and its vector embeddings."
      )
    ) {
      return;
    }
    try {
      await api.delete(`/contracts/${contractId}`);
      removeContract(contractId);
    } catch (err) {
      console.error("Failed to delete contract:", err);
      alert("Failed to delete contract. Please try again.");
    }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case "pending":
        return "badge-pending";
      case "ingested":
      case "analyzed":
        return "badge-success";
      case "failed":
        return "badge-danger";
      default:
        return "badge-muted";
    }
  };

  // Filter contracts based on global search query
  const filteredContracts = contracts.filter((c) =>
    c.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="dashboard-page-content">
      {/* Workspace Header */}
      <section className="mb-4 flex-between-end-wrap">
        <div>
          <h1 className="title-large">Contract Vault</h1>
          <p className="mt-1">
            Manage your legal documents, trigger multi-agent analyses, and inspect risk profiles
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => navigate("/contracts/upload")}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
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
          Upload New Document
        </button>
      </section>

      <div className="grid-main-sidebar dashboard-grid">
        {/* Contracts List Panel */}
        <div className="glass-panel panel-padded-lg min-h-400">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 className="title-panel" style={{ marginBottom: 0 }}>
              Active Contracts ({filteredContracts.length})
            </h3>
            {searchQuery && (
              <span style={{ fontSize: "0.8rem", color: "var(--color-text-muted)" }}>
                Filtering by: "{searchQuery}"
              </span>
            )}
          </div>

          {isLoading ? (
            <div className="flex-center-h200">
              <div className="spinner" />
            </div>
          ) : filteredContracts.length === 0 ? (
            <div className="empty-state-container">
              <svg
                width="48"
                height="48"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                viewBox="0 0 24 24"
                className="icon-muted-lg"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                />
              </svg>
              <p className="text-semibold-md">
                {searchQuery ? "No matching contracts found." : "No contracts uploaded yet."}
              </p>
              <p className="text-muted-sm-mt1">
                {searchQuery ? "Try searching for a different keyword." : "Upload a PDF, scan, or Word doc on the right to start analysis."}
              </p>
            </div>
          ) : (
            <div className="table-wrapper overflow-x-auto">
              <table className="contracts-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Upload Date</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredContracts.map((contract) => (
                    <tr key={contract.id}>
                      <td className="text-bold-main">
                        <div
                          style={{ cursor: "pointer", color: "var(--color-text-main)", display: "flex", alignItems: "center", gap: "8px" }}
                          onClick={() => navigate(`/contracts/${contract.id}`)}
                          title="Open Contract Workspace"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="var(--color-primary)"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                          </svg>
                          <span>{contract.filename}</span>
                        </div>
                      </td>
                      <td>{formatDate(contract.created_at)}</td>
                      <td>
                        <span className={`badge ${getStatusBadgeClass(contract.status)}`}>
                          {contract.status}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: "flex", gap: "8px" }}>
                          <button
                            className="btn btn-secondary btn-table-action"
                            onClick={() => navigate(`/contracts/${contract.id}`)}
                          >
                            View Analysis
                          </button>
                          <button
                            className="btn btn-danger-outline btn-table-action"
                            onClick={() => handleDeleteContract(contract.id)}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Quick Upload Panel */}
        <div className="glass-panel panel-padded-lg">
          <h3 className="title-panel-sm">Quick Upload</h3>
          <p className="text-muted-desc">
            Upload contracts in PDF, Photo Scans (PNG, JPG, WEBP), Word (.docx), or Text (.txt). Max 10MB.
          </p>

          {uploadError && <div className="alert alert-danger alert-sm">{uploadError}</div>}

          {uploadSuccess && <div className="alert alert-success alert-sm">File uploaded successfully!</div>}

          <div className="upload-dropzone">
            <input
              type="file"
              id="contract-file-upload"
              accept=".pdf, .png, .jpg, .jpeg, .webp, .tiff, .bmp, .docx, .doc, .txt, .md, .rtf, image/*"
              onChange={handleFileUpload}
              disabled={isUploading}
              className="d-none"
            />
            <label htmlFor="contract-file-upload" className="dropzone-label">
              {isUploading ? (
                <div className="flex-column-center-gap2">
                  <div className="spinner" />
                  <span className="text-semibold-sm">Uploading & Indexing...</span>
                </div>
              ) : (
                <>
                  <svg
                    width="32"
                    height="32"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    viewBox="0 0 24 24"
                    className="icon-primary-md"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z"
                    />
                  </svg>
                  <span className="text-bold-md">Choose Document or Photo</span>
                  <span className="text-dark-xs-mt1">Supports PDF, JPG, PNG, DOCX, TXT</span>
                </>
              )}
            </label>
          </div>
        </div>
      </div>

      <style>{`
        .contracts-table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
          font-size: 0.9rem;
        }
        .contracts-table th, .contracts-table td {
          padding: 14px 16px;
          border-bottom: 1px solid var(--color-border);
        }
        .contracts-table th {
          color: var(--color-text-muted);
          font-weight: 500;
          font-size: 0.85rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .contracts-table tbody tr {
          transition: background-color var(--transition-fast);
        }
        .contracts-table tbody tr:hover {
          background-color: rgba(255, 255, 255, 0.02);
        }
        
        .badge {
          display: inline-flex;
          align-items: center;
          padding: 4px 10px;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: capitalize;
          border: 1px solid transparent;
        }
        .badge-pending {
          background: rgba(56, 189, 248, 0.1);
          color: #7dd3fc;
          border-color: rgba(56, 189, 248, 0.2);
        }
        .badge-success {
          background: var(--color-success-bg);
          color: #a7f3d0;
          border-color: rgba(16, 185, 129, 0.2);
        }
        .badge-danger {
          background: var(--color-danger-bg);
          color: #fda4af;
          border-color: rgba(244, 63, 94, 0.2);
        }
        
        .upload-dropzone {
          border: 2px dashed var(--color-border);
          border-radius: 12px;
          background: rgba(255, 255, 255, 0.01);
          transition: border-color var(--transition-fast), background var(--transition-fast);
        }
        .upload-dropzone:hover {
          border-color: var(--color-primary);
          background: rgba(92, 98, 236, 0.02);
        }
        .dropzone-label {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 40px 20px;
          cursor: pointer;
          width: 100%;
        }
        
        @media (max-width: 900px) {
          .dashboard-grid {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
};
