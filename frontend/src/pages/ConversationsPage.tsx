import React, { useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "../store/useAuthStore";
import {
  fetchConversations,
  updateConversationTitle,
  deleteConversation,
  type ConversationItem,
} from "../services/historyService";
import { ConfirmModal } from "../components/ConfirmModal";
import { Skeleton } from "../components/Skeleton";
import { useToast } from "../context/ToastContext";
import "./ConversationsPage.css";

export const ConversationsPage: React.FC = () => {
  const user = useAuthStore((state) => state.user);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { success, error } = useToast();

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedContractFilter, setSelectedContractFilter] = useState<string>("ALL");
  const [editingConvoId, setEditingConvoId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [deleteModalState, setDeleteModalState] = useState<{
    isOpen: boolean;
    convoId: number | null;
    convoTitle: string;
  }>({
    isOpen: false,
    convoId: null,
    convoTitle: "",
  });

  // Query Conversations
  const { data: conversations = [], isLoading, refetch } = useQuery({
    queryKey: ["conversations", user?.id],
    queryFn: () => fetchConversations(),
    enabled: !!user?.id,
    staleTime: 20000,
  });

  // Rename Mutation
  const renameMutation = useMutation({
    mutationFn: ({ id, title }: { id: number; title: string }) =>
      updateConversationTitle(id, title),
    onSuccess: (updated) => {
      queryClient.setQueryData<ConversationItem[]>(
        ["conversations", user?.id],
        (old = []) => old.map((c) => (c.id === updated.id ? { ...c, title: updated.title } : c))
      );
      success("Conversation title updated.");
      setEditingConvoId(null);
    },
    onError: () => {
      error("Failed to update conversation title.");
    },
  });

  // Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteConversation(id),
    onSuccess: (_, deletedId) => {
      queryClient.setQueryData<ConversationItem[]>(
        ["conversations", user?.id],
        (old = []) => old.filter((c) => c.id !== deletedId)
      );
      success("Conversation thread deleted.");
      setDeleteModalState({ isOpen: false, convoId: null, convoTitle: "" });
    },
    onError: () => {
      error("Failed to delete conversation thread.");
    },
  });

  // Unique Contracts in Conversations
  const contractOptions = useMemo(() => {
    const map = new Map<number, string>();
    conversations.forEach((c) => {
      if (c.contract_filename) {
        map.set(c.contract_id, c.contract_filename);
      }
    });
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [conversations]);

  // Filtered Conversations
  const filteredConversations = useMemo(() => {
    return conversations.filter((c) => {
      const matchesContract =
        selectedContractFilter === "ALL" ||
        String(c.contract_id) === selectedContractFilter;

      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !q ||
        c.title.toLowerCase().includes(q) ||
        (c.contract_filename && c.contract_filename.toLowerCase().includes(q));

      return matchesContract && matchesSearch;
    });
  }, [conversations, selectedContractFilter, searchQuery]);

  // Aggregate Stats
  const stats = useMemo(() => {
    const totalQuestions = conversations.reduce((acc, c) => acc + (c.message_count || 0), 0);
    const uniqueDocs = new Set(conversations.map((c) => c.contract_id)).size;
    return {
      total: conversations.length,
      totalQuestions,
      uniqueDocs,
    };
  }, [conversations]);

  const handleStartRename = (c: ConversationItem) => {
    setEditingConvoId(c.id);
    setEditingTitle(c.title);
  };

  const handleSaveRename = (id: number) => {
    if (!editingTitle.trim()) return;
    renameMutation.mutate({ id, title: editingTitle.trim() });
  };

  const handleConfirmDelete = () => {
    if (deleteModalState.convoId) {
      deleteMutation.mutate(deleteModalState.convoId);
    }
  };

  const formatLastActive = (iso: string) => {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  return (
    <div className="convos-page-container">
      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={deleteModalState.isOpen}
        title="Delete Conversation Thread"
        message={`Are you sure you want to delete the thread "${deleteModalState.convoTitle}"? All messages and citations will be permanently removed.`}
        confirmText="Delete Thread"
        variant="danger"
        isLoading={deleteMutation.isPending}
        onConfirm={handleConfirmDelete}
        onClose={() => setDeleteModalState({ isOpen: false, convoId: null, convoTitle: "" })}
      />

      {/* Hero Header */}
      <div className="convos-hero-card">
        <div className="convos-hero-top">
          <div>
            <div className="convos-hero-badge">
              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              Persistent Document Discussions
            </div>
            <h1 className="convos-hero-title">Q&A Conversation Archives</h1>
            <p className="convos-hero-desc">
              Reopen any historical conversational inquiry across your contract vault. Every dialogue
              turn is preserved with pinpoint clause citations, similarity metrics, and context.
            </p>
          </div>

          <div style={{ display: "flex", gap: "10px" }}>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => navigate("/history")}
              title="Switch to full audit trail"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
              <span>Activity Timeline</span>
            </button>

            <button
              className="btn btn-primary btn-sm"
              onClick={() => navigate("/dashboard")}
              title="Open contract vault to start Q&A"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              <span>New Conversation</span>
            </button>
          </div>
        </div>

        {/* Aggregate Stats */}
        <div className="convos-stats-grid">
          <div className="convos-stat-box">
            <span className="convos-stat-num">{stats.total}</span>
            <span className="convos-stat-label">Saved Discussions</span>
          </div>
          <div className="convos-stat-box">
            <span className="convos-stat-num" style={{ color: "#34d399" }}>
              {stats.totalQuestions}
            </span>
            <span className="convos-stat-label">Total Messages & Answers</span>
          </div>
          <div className="convos-stat-box">
            <span className="convos-stat-num" style={{ color: "#38bdf8" }}>
              {stats.uniqueDocs}
            </span>
            <span className="convos-stat-label">Documents Discussed</span>
          </div>
        </div>
      </div>

      {/* Control Bar */}
      <div className="convos-filter-bar">
        <div className="convos-search-input-wrapper">
          <svg className="convos-search-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="convos-search-input"
            placeholder="Search conversations by title or document..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          {contractOptions.length > 0 && (
            <select
              className="history-date-select"
              value={selectedContractFilter}
              onChange={(e) => setSelectedContractFilter(e.target.value)}
            >
              <option value="ALL">All Documents ({contractOptions.length})</option>
              {contractOptions.map((co) => (
                <option key={co.id} value={String(co.id)}>
                  {co.name}
                </option>
              ))}
            </select>
          )}

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => refetch()}
            title="Refresh threads"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
            </svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Grid of Conversations */}
      {isLoading ? (
        <div className="convos-grid">
          <Skeleton height={200} borderRadius={16} />
          <Skeleton height={200} borderRadius={16} />
          <Skeleton height={200} borderRadius={16} />
        </div>
      ) : filteredConversations.length === 0 ? (
        <div className="history-empty-card">
          <div className="history-empty-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <h3 className="history-empty-title">No Conversations Found</h3>
          <p className="history-empty-desc">
            {conversations.length === 0
              ? "You haven't asked any questions about your contracts yet. Open a contract in the vault and start a grounded Q&A thread!"
              : "No conversation threads matched your search query."}
          </p>
          <button className="btn btn-primary btn-sm" onClick={() => navigate("/dashboard")}>
            Browse Contract Vault
          </button>
        </div>
      ) : (
        <div className="convos-grid">
          {filteredConversations.map((convo) => {
            const isEditing = editingConvoId === convo.id;

            return (
              <div key={convo.id} className="convo-card">
                <div>
                  {/* Header: Contract badge and message count */}
                  <div className="convo-card-header">
                    <Link
                      to={`/contracts/${convo.contract_id}`}
                      className="convo-contract-badge"
                      title={convo.contract_filename || "Document"}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <span>{convo.contract_filename || `Contract #${convo.contract_id}`}</span>
                    </Link>

                    <span className="convo-msg-count-pill">
                      {convo.message_count ?? 0} {convo.message_count === 1 ? "turn" : "turns"}
                    </span>
                  </div>

                  {/* Body: Title & Date */}
                  <div className="convo-card-body" style={{ marginTop: "14px" }}>
                    {isEditing ? (
                      <div style={{ display: "flex", gap: "6px" }}>
                        <input
                          type="text"
                          className="convo-rename-input"
                          value={editingTitle}
                          onChange={(e) => setEditingTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") handleSaveRename(convo.id);
                            if (e.key === "Escape") setEditingConvoId(null);
                          }}
                          autoFocus
                        />
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={() => handleSaveRename(convo.id)}
                          disabled={renameMutation.isPending}
                        >
                          Save
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => setEditingConvoId(null)}
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <div className="convo-title-row">
                        <h3 className="convo-title">{convo.title}</h3>
                        <button
                          className="btn-icon-rename"
                          onClick={() => handleStartRename(convo)}
                          title="Rename title"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </button>
                      </div>
                    )}

                    <span className="convo-time-info">
                      Last inquiry: {formatLastActive(convo.last_message_at)}
                    </span>
                  </div>
                </div>

                {/* Footer: Resume and Delete */}
                <div className="convo-card-footer">
                  <Link
                    to={`/contracts/${convo.contract_id}/ask?conversation_id=${convo.id}`}
                    className="btn-resume-convo"
                  >
                    <span>Resume Discussion</span>
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </Link>

                  <button
                    className="btn-icon-danger"
                    onClick={() =>
                      setDeleteModalState({
                        isOpen: true,
                        convoId: convo.id,
                        convoTitle: convo.title,
                      })
                    }
                    title="Delete thread"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ConversationsPage;
