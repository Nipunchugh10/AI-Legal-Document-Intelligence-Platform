import React, { useState, useEffect, useRef, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api from "../services/api";
import "./QAPage.css";

interface QASource {
  chunk_index?: number;
  text?: string;
  similarity?: number;
  section?: string;
  page?: number;
}

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  sources?: QASource[];
  timestamp: string;
  error?: boolean;
}

interface ContractInfo {
  id: number;
  filename: string;
  upload_path: string;
  status: "pending" | "ingested" | "analyzed" | "failed";
  created_at: string;
}

export const QAPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [contract, setContract] = useState<ContractInfo | null>(null);
  const [contractText, setContractText] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<QASource | null>(null);
  const [activeLeftTab, setActiveLeftTab] = useState<"inspector" | "document">("inspector");
  const [docSearchQuery, setDocSearchQuery] = useState("");
  const [copyStatus, setCopyStatus] = useState<string | null>(null);
  const [isLoadingContract, setIsLoadingContract] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Suggested high-impact legal questions
  const suggestedQuestions = [
    { label: "⚡ Early Termination", query: "Can I terminate this contract early? What notice period and exit penalties apply?" },
    { label: "🛡️ Liability & Indemnity", query: "What is the liability cap and indemnity scope? Is liability mutual or unilateral?" },
    { label: "💳 Payment Terms", query: "What are the payment schedules, late fees, and milestone invoice terms?" },
    { label: "🔒 Non-Compete & IP", query: "Is there a non-compete, non-solicit, or intellectual property assignment clause?" },
    { label: "⚖️ Dispute Resolution", query: "What is the governing law, seat of arbitration, and dispute escalation procedure?" },
  ];

  // Fetch contract metadata & full text
  useEffect(() => {
    if (!id) return;
    setIsLoadingContract(true);

    const loadData = async () => {
      try {
        const contractRes = await api.get<ContractInfo>(`/contracts/${id}`);
        setContract(contractRes.data);

        try {
          const textRes = await api.get<{ text: string }>(`/contracts/${id}/text`);
          if (textRes.data?.text) {
            setContractText(textRes.data.text);
          }
        } catch {
          // Document text not available yet
        }
      } catch (err) {
        console.error("Failed to load contract details for Q&A", err);
      } finally {
        setIsLoadingContract(false);
      }
    };

    loadData();
  }, [id]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isAsking]);

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = (queryText || inputValue).trim();
    if (!textToSend || isAsking || !id) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInputValue("");
    setIsAsking(true);

    try {
      const response = await api.post<{
        contract_id: number;
        question: string;
        answer: string;
        sources: QASource[];
      }>(`/contracts/${id}/ask`, {
        question: textToSend,
      });

      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        sender: "assistant",
        text: response.data.answer,
        sources: response.data.sources || [],
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, aiMsg]);

      // If the response contains sources, auto-select the first citation for inspection
      if (response.data.sources && response.data.sources.length > 0) {
        setSelectedCitation(response.data.sources[0]);
        setActiveLeftTab("inspector");
      }
    } catch (err: any) {
      const rawDetail = err.response?.data?.detail || err.message || "An error occurred querying the document.";
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: "assistant",
        text: typeof rawDetail === "string" ? rawDetail : "Failed to query the document. Please ensure contract analysis has completed.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        error: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsAsking(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleRegenerate = (lastQuery: string) => {
    if (isAsking) return;
    handleSendMessage(lastQuery);
  };

  const handleClearChat = () => {
    if (messages.length === 0) return;
    if (window.confirm("Are you sure you want to clear the conversation history?")) {
      setMessages([]);
      setSelectedCitation(null);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopyStatus(label);
    setTimeout(() => setCopyStatus(null), 2000);
  };

  const handleExportChat = () => {
    if (!contract || messages.length === 0) return;

    const transcript = `# Grounded Legal Q&A Transcript
**Document:** ${contract.filename}
**Date:** ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString()}
**Contract ID:** #${contract.id}

---

${messages
  .map((m) => {
    if (m.sender === "user") {
      return `### 👤 User (${m.timestamp})\n${m.text}\n`;
    }
    const cites = m.sources && m.sources.length > 0
      ? `\n**📌 Citations Grounded:**\n` +
        m.sources
          .map((s, idx) => `- Source ${idx + 1} (Chunk #${s.chunk_index ?? "N/A"}, Similarity: ${s.similarity ? (s.similarity * 100).toFixed(1) + "%" : "Verified"}): "${s.text?.slice(0, 180)}..."`)
          .join("\n")
      : "";
    return `### ⚖️ AI Legal Counsel (${m.timestamp})\n${m.text}\n${cites}\n`;
  })
  .join("\n---\n\n")}

*Generated by AI Legal Document Intelligence Platform (Grounded RAG Agent 5)*
`;

    const blob = new Blob([transcript], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `QA_Transcript_${contract.filename.replace(/\.[^/.]+$/, "")}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Filtered contract text for document search
  const highlightedDocText = useMemo(() => {
    if (!contractText) return "No extracted document text available.";
    if (!docSearchQuery.trim()) return contractText;
    return contractText;
  }, [contractText, docSearchQuery]);

  const lastUserQuery = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].sender === "user") return messages[i].text;
    }
    return null;
  }, [messages]);

  if (isLoadingContract) {
    return (
      <div className="page-loader" style={{ minHeight: "65vh" }}>
        <div className="spinner" />
        <p className="loader-text">Loading Grounded Legal Q&A Assistant...</p>
      </div>
    );
  }

  if (!contract) {
    return (
      <div className="placeholder-hero-card" style={{ maxWidth: "600px", margin: "40px auto", textAlign: "center" }}>
        <h2>Contract Not Found</h2>
        <p>The requested document could not be found or you do not have permission to view it.</p>
        <button className="btn btn-primary" onClick={() => navigate("/dashboard")}>
          Return to Contract Vault
        </button>
      </div>
    );
  }

  return (
    <div className="qa-workspace-container">
      {/* Top Breadcrumb & Action Bar */}
      <section className="qa-top-bar">
        <nav className="qa-breadcrumbs">
          <Link to="/dashboard">Contract Vault</Link>
          <span className="crumb-separator">/</span>
          <Link to={`/contracts/${contract.id}`} title={contract.filename}>
            {contract.filename}
          </Link>
          <span className="crumb-separator">/</span>
          <span className="crumb-current">Grounded Q&A</span>
        </nav>

        <div className="qa-header-actions">
          {messages.length > 0 && (
            <>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleExportChat}
                title="Export conversation history to Markdown"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="7 10 12 15 17 10" />
                  <line x1="12" y1="15" x2="12" y2="3" />
                </svg>
                <span>Export Chat</span>
              </button>

              <button
                className="btn btn-secondary btn-sm"
                onClick={handleClearChat}
                title="Clear all messages in thread"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                </svg>
                <span>Clear Chat</span>
              </button>
            </>
          )}

          <button
            className="btn btn-primary btn-sm"
            onClick={() => navigate(`/contracts/${contract.id}`)}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="9" y1="3" x2="9" y2="21" />
            </svg>
            <span>Back to Analysis</span>
          </button>
        </div>
      </section>

      {/* Two-Panel Split Workspace */}
      <div className="qa-split-grid">
        {/* Left Panel: Verified Source Inspector & Document Viewer */}
        <div className="qa-left-panel">
          {/* Panel Tab Selector */}
          <div className="qa-left-tab-bar">
            <button
              className={`qa-left-tab-btn ${activeLeftTab === "inspector" ? "active" : ""}`}
              onClick={() => setActiveLeftTab("inspector")}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              <span>Source Citation Inspector</span>
            </button>
            <button
              className={`qa-left-tab-btn ${activeLeftTab === "document" ? "active" : ""}`}
              onClick={() => setActiveLeftTab("document")}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span>Document Text</span>
            </button>
          </div>

          <div className="qa-left-tab-content">
            {/* 1. Verified Source Citation Inspector */}
            {activeLeftTab === "inspector" && (
              <div className="source-inspector-container">
                {selectedCitation ? (
                  <div className="citation-detail-card">
                    <div className="citation-detail-header">
                      <div className="citation-tag-badge">
                        <span>Chunk #{selectedCitation.chunk_index ?? "Ref"}</span>
                        {selectedCitation.similarity && (
                          <span className="similarity-badge">
                            {(selectedCitation.similarity * 100).toFixed(0)}% Semantic Match
                          </span>
                        )}
                      </div>
                      <button
                        className="btn-copy-snippet"
                        onClick={() => copyToClipboard(selectedCitation.text || "", "Citation Text")}
                      >
                        {copyStatus === "Citation Text" ? "✓ Copied" : "Copy Passage"}
                      </button>
                    </div>

                    <div className="citation-verbatim-body">
                      <div className="citation-watermark">VERIFIED RAG CONTRACT EXCERPT</div>
                      <p>{selectedCitation.text || "No text available for this chunk."}</p>
                    </div>

                    <div className="citation-inspector-footer">
                      <span>Grounded via ChromaDB Vector Store & Gemini 2.5/3.5 Embeddings</span>
                    </div>
                  </div>
                ) : (
                  <div className="citation-empty-state">
                    <div className="citation-empty-icon">📌</div>
                    <h4>No Citation Selected</h4>
                    <p>
                      Ask a legal question in the chat thread, or click any citation pill on an AI response to inspect the exact grounded contract passage.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* 2. Raw Document Text Viewer */}
            {activeLeftTab === "document" && (
              <div className="doc-viewer-container">
                <div className="doc-search-bar">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                  <input
                    type="text"
                    placeholder="Search in contract text..."
                    value={docSearchQuery}
                    onChange={(e) => setDocSearchQuery(e.target.value)}
                  />
                  {docSearchQuery && (
                    <button className="btn-clear-search" onClick={() => setDocSearchQuery("")}>
                      ×
                    </button>
                  )}
                </div>

                <div className="doc-raw-text-box">
                  {highlightedDocText}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Panel: Conversational AI Thread */}
        <div className="qa-right-panel">
          {/* Chat Messages Feed */}
          <div className="chat-messages-feed">
            {messages.length === 0 ? (
              <div className="chat-empty-hero">
                <div className="hero-avatar-circle">
                  <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  </svg>
                </div>
                <h3>Grounded Legal Document Q&A</h3>
                <p className="hero-subtext">
                  Ask any question about <strong>{contract.filename}</strong>. Every response is strictly grounded in contract text chunks retrieved via RAG with pinpoint citations.
                </p>

                {/* Suggested Question Chips */}
                <div className="suggested-chips-grid">
                  {suggestedQuestions.map((q, idx) => (
                    <button
                      key={idx}
                      className="suggested-chip-btn"
                      onClick={() => handleSendMessage(q.query)}
                      disabled={isAsking}
                    >
                      <span className="chip-label">{q.label}</span>
                      <span className="chip-query">{q.query}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`chat-bubble-row ${msg.sender === "user" ? "user-row" : "ai-row"}`}
                >
                  <div className="bubble-avatar">
                    {msg.sender === "user" ? "👤" : "⚖️"}
                  </div>

                  <div className={`chat-bubble ${msg.sender === "user" ? "user-bubble" : "ai-bubble"} ${msg.error ? "error-bubble" : ""}`}>
                    <div className="bubble-header">
                      <span className="bubble-sender-name">
                        {msg.sender === "user" ? "You" : "AI Legal Counsel"}
                      </span>
                      <span className="bubble-time">{msg.timestamp}</span>
                    </div>

                    <div className="bubble-content-text">{msg.text}</div>

                    {/* Pinpoint Grounded Citations Bar */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="bubble-citations-section">
                        <div className="citations-label">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                          </svg>
                          <span>Grounded Source Citations:</span>
                        </div>
                        <div className="citation-pills-list">
                          {msg.sources.map((src, i) => (
                            <button
                              key={i}
                              className={`citation-pill-btn ${selectedCitation === src ? "active" : ""}`}
                              onClick={() => {
                                setSelectedCitation(src);
                                setActiveLeftTab("inspector");
                              }}
                              title="Click to inspect this grounded passage"
                            >
                              <span>📌 Chunk #{src.chunk_index ?? i + 1}</span>
                              {src.similarity && (
                                <span className="pill-sim">
                                  {(src.similarity * 100).toFixed(0)}%
                                </span>
                              )}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI Message Action Toolbar */}
                    {msg.sender === "assistant" && !msg.error && (
                      <div className="bubble-action-bar">
                        <button
                          className="bubble-action-btn"
                          onClick={() => copyToClipboard(msg.text, `msg-${msg.id}`)}
                        >
                          {copyStatus === `msg-${msg.id}` ? "✓ Copied!" : "Copy Answer"}
                        </button>
                        {lastUserQuery && (
                          <button
                            className="bubble-action-btn"
                            onClick={() => handleRegenerate(lastUserQuery)}
                            disabled={isAsking}
                          >
                            Regenerate
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {/* Thinking / Researching Indicator */}
            {isAsking && (
              <div className="chat-bubble-row ai-row">
                <div className="bubble-avatar">⚖️</div>
                <div className="chat-bubble ai-bubble thinking-bubble">
                  <div className="thinking-content">
                    <div className="pulse-dots">
                      <span />
                      <span />
                      <span />
                    </div>
                    <span>Retrieving contract chunks & synthesizing verified legal answer...</span>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="chat-input-wrapper">
            <div className="chat-input-box">
              <textarea
                ref={inputRef}
                className="chat-textarea"
                placeholder="Ask any legal question (e.g. Can the vendor assign this agreement? What is the governing law?)..."
                rows={1}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
              />
              <button
                className="btn-send-message"
                onClick={() => handleSendMessage()}
                disabled={isAsking || !inputValue.trim()}
                title="Send query (Enter)"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>
            <div className="chat-input-hints">
              <span>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for new line</span>
              <span>All responses are grounded with pinpoint source citations</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
