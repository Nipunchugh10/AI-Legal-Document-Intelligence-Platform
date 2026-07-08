import React, { useEffect, useState } from "react";
import api from "../services/api";
import { useAuthStore } from "../store/useAuthStore";
import { useNavigate } from "react-router-dom";

interface Contract {
  id: number;
  filename: string;
  upload_path: string;
  status: "pending" | "ingested" | "analyzed" | "failed";
  created_at: string;
}

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  
  const [contracts, setContracts] = useState<Contract[]>([]);
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

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    setUploadError(null);
    setUploadSuccess(false);
    setIsUploading(true);

    // Client-side validations
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Only PDF files are allowed.");
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
      // Reset input
      e.target.value = "";
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

  return (
    <div className="app-container">
      {/* Navbar Component */}
      <header className="navbar">
        <div className="navbar-brand">
          Legal<span>Intelligence</span>
        </div>
        <div className="navbar-actions">
          <span className="user-email">{user?.email}</span>
          <button onClick={() => navigate("/security")} className="btn btn-secondary btn-nav-action">
            Security Settings
          </button>
          <button onClick={handleLogout} className="btn btn-secondary btn-nav-action">
            Sign Out
          </button>
        </div>
      </header>

      {/* Main Workspace Dashboard */}
      <main className="main-content page-container">
        {/* Welcome Section */}
        <section className="mb-4 flex-between-end-wrap">
          <div>
            <h1 className="title-large">Workspace</h1>
            <p className="mt-1">Analyze documents, track risks, and manage your legal workflow</p>
          </div>
        </section>

        <div className="grid-main-sidebar dashboard-grid">
          {/* Contracts List Panel */}
          <div className="glass-panel panel-padded-lg min-h-400">
            <h3 className="title-panel">Your Contracts</h3>

            {isLoading ? (
              <div className="flex-center-h200">
                <div className="spinner" />
              </div>
            ) : contracts.length === 0 ? (
              <div className="empty-state-container">
                <svg width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="icon-muted-lg">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
                <p className="text-semibold-md">No contracts uploaded yet.</p>
                <p className="text-muted-sm-mt1">Upload a PDF on the right to start analysis.</p>
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
                    {contracts.map((contract) => (
                      <tr key={contract.id}>
                        <td className="text-bold-main">
                          {contract.filename}
                        </td>
                        <td>{formatDate(contract.created_at)}</td>
                        <td>
                          <span className={`badge ${getStatusBadgeClass(contract.status)}`}>
                            {contract.status}
                          </span>
                        </td>
                        <td>
                          <button 
                            className="btn btn-secondary btn-table-action" 
                            onClick={() => alert(`Day 16+ parsing details will open contract ${contract.id}`)}
                          >
                            View Analysis
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Upload Sidebar */}
          <div className="glass-panel panel-padded-lg">
            <h3 className="title-panel-sm">Upload Document</h3>
            <p className="text-muted-desc">
              Upload your agreement in PDF format. We support file sizes up to 10MB.
            </p>

            {uploadError && (
              <div className="alert alert-danger alert-sm">
                {uploadError}
              </div>
            )}

            {uploadSuccess && (
              <div className="alert alert-success alert-sm">
                File uploaded successfully!
              </div>
            )}

            <div className="upload-dropzone">
              <input
                type="file"
                id="contract-file-upload"
                accept=".pdf"
                onChange={handleFileUpload}
                disabled={isUploading}
                className="d-none"
              />
              <label htmlFor="contract-file-upload" className="dropzone-label">
                {isUploading ? (
                  <div className="flex-column-center-gap2">
                    <div className="spinner" />
                    <span className="text-semibold-sm">Uploading file...</span>
                  </div>
                ) : (
                  <>
                    <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24" className="icon-primary-md">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                    </svg>
                    <span className="text-bold-md">Choose PDF file</span>
                    <span className="text-dark-xs-mt1">Click to select files</span>
                  </>
                )}
              </label>
            </div>
          </div>
        </div>
      </main>

      {/* Styled Dashboard Components (Local CSS overrides) */}
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
