import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "../services/api";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  citations?: Array<{
    page?: number;
    clause?: string;
    section?: string;
    text?: string;
  }>;
  timestamp: string;
}

export const QAPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [contractName, setContractName] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) return;
    api
      .get(`/contracts/${id}`)
      .then((res) => setContractName(res.data.filename))
      .catch((err) => console.error("Failed to load contract name", err));
  }, [id]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isAsking]);

  const handleSendMessage = async (queryText?: string) => {
    const textToSend = queryText || inputValue;
    if (!textToSend.trim() || isAsking || !id) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: "user",
      text: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInputValue("");
    setIsAsking(true);

    try {
      const response = await api.post(`/contracts/${id}/ask`, {
        question: textToSend,
      });

      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        text: response.data.answer,
        citations: response.data.sources || response.data.citations,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        text: err.response?.data?.detail || "Sorry, I encountered an error searching this document. Please ensure analysis has been run on this contract first.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsAsking(false);
    }
  };

  const suggestedQuestions = [
    "Can I terminate this contract early?",
    "What is the liability cap and indemnity scope?",
    "What are the payment and milestone terms?",
    "Is there a non-compete or IP assignment clause?",
  ];

  return (
    <div className="placeholder-view-container">
      {/* Header bar */}
      <div className="placeholder-hero-card" style={{ padding: "20px 28px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
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
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              Grounded Legal Q&A Agent
            </div>
            <h2 style={{ fontSize: "1.4rem", marginTop: "6px", fontWeight: "700" }}>
              {contractName ? `Q&A: ${contractName}` : "Contract Intelligence Chat"}
            </h2>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/contracts/${id}`)}>
            Back to Analysis
          </button>
        </div>
      </div>

      {/* Chat Container */}
      <div
        className="glass-panel"
        style={{
          display: "flex",
          flexDirection: "column",
          height: "62vh",
          padding: "0",
          overflow: "hidden",
          borderRadius: "16px",
        }}
      >
        {/* Messages Feed */}
        <div style={{ flex: 1, padding: "24px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "16px" }}>
          {messages.length === 0 ? (
            <div style={{ margin: "auto", textAlign: "center", maxWidth: "500px" }}>
              <div
                style={{
                  width: "48px",
                  height: "48px",
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
                  width="24"
                  height="24"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <h3 style={{ fontSize: "1.2rem", fontWeight: "600", marginBottom: "8px" }}>
                Ask anything about this document
              </h3>
              <p style={{ fontSize: "0.88rem", color: "var(--color-text-muted)", marginBottom: "20px" }}>
                Every answer is verified against your contract's vector embeddings and statutory legal benchmarks.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {suggestedQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    className="btn btn-secondary btn-sm"
                    style={{ textAlign: "left", justifyContent: "flex-start" }}
                    onClick={() => handleSendMessage(q)}
                  >
                    💬 {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: msg.sender === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    maxWidth: "75%",
                    padding: "14px 18px",
                    borderRadius: "14px",
                    background:
                      msg.sender === "user"
                        ? "linear-gradient(135deg, var(--color-primary) 0%, #4338ca 100%)"
                        : "rgba(255, 255, 255, 0.04)",
                    border: msg.sender === "user" ? "none" : "1px solid var(--color-border)",
                    color: "#fff",
                    fontSize: "0.92rem",
                    lineHeight: "1.6",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {msg.text}

                  {/* Citations block */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div style={{ marginTop: "10px", borderTop: "1px solid rgba(255, 255, 255, 0.1)", paddingTop: "8px" }}>
                      <span style={{ fontSize: "0.75rem", color: "var(--color-secondary)", fontWeight: "600" }}>
                        📌 Grounded Sources Cited:
                      </span>
                      {msg.citations.map((cite, i) => (
                        <div key={i} style={{ fontSize: "0.78rem", color: "var(--color-text-muted)", marginTop: "2px" }}>
                          • {cite.clause || cite.section || "Clause reference"} {cite.page ? `(Page ${cite.page})` : ""}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                <span style={{ fontSize: "0.72rem", color: "var(--color-text-dark)", marginTop: "4px", padding: "0 4px" }}>
                  {msg.timestamp}
                </span>
              </div>
            ))
          )}

          {isAsking && (
            <div style={{ display: "flex", alignItems: "center", gap: "10px", color: "var(--color-text-muted)", fontSize: "0.88rem" }}>
              <div className="spinner spinner-sm" />
              <span>Grounded Agent is researching contract clauses...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div style={{ padding: "16px 20px", borderTop: "1px solid var(--color-border)", background: "rgba(0, 0, 0, 0.2)", display: "flex", gap: "12px" }}>
          <input
            type="text"
            className="form-control"
            style={{ flex: 1 }}
            placeholder="Ask a question about this contract (e.g. What are my obligations on termination?)..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
          />
          <button className="btn btn-primary" onClick={() => handleSendMessage()} disabled={isAsking || !inputValue.trim()}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
};
