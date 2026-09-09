/**
 * History & Conversation Service
 * -------------------------------
 * API client methods and TypeScript contracts for Activity History
 * and Stateful Q&A Conversation Threads.
 *
 * Day 47 — Activity History Frontend
 */

import api from "./api";

export interface AuditLogItem {
  id: number;
  user_id?: number;
  action: string;
  resource_id?: number;
  status: "SUCCESS" | "FAILURE" | string;
  ip_address?: string;
  user_agent?: string;
  metadata_json?: Record<string, any>;
  timestamp: string;
  category: "AUTH" | "CONTRACTS" | "ANALYSIS" | "CHAT" | "SEARCH" | "SECURITY" | "GENERAL";
  description: string;
}

export interface AuditLogFeedResponse {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface ConversationItem {
  id: number;
  user_id: number;
  contract_id: number;
  title: string;
  created_at: string;
  last_message_at: string;
  message_count?: number;
  contract_filename?: string;
}

export interface CitedClauseRef {
  chunk_index?: number;
  text?: string;
  similarity?: number;
  section?: string;
  page?: number;
  clause_id?: string;
}

export interface ConversationMessageItem {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "system";
  content: string;
  cited_clause_refs?: CitedClauseRef[];
  created_at: string;
}

export interface ConversationDetail {
  id: number;
  user_id: number;
  contract_id: number;
  title: string;
  created_at: string;
  last_message_at: string;
  message_count: number;
  contract_filename?: string;
  messages: ConversationMessageItem[];
}

export interface HistoryFilterParams {
  category?: string;
  action?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

/**
 * Retrieves paginated and filtered activity audit timeline entries.
 */
export async function fetchActivityHistory(
  params: HistoryFilterParams = {}
): Promise<AuditLogFeedResponse> {
  const query = new URLSearchParams();

  if (params.category && params.category !== "ALL") {
    query.set("category", params.category);
  }
  if (params.action) {
    query.set("action", params.action);
  }
  if (params.status && params.status !== "ALL") {
    query.set("status", params.status);
  }
  if (params.start_date) {
    query.set("start_date", params.start_date);
  }
  if (params.end_date) {
    query.set("end_date", params.end_date);
  }
  if (params.limit) {
    query.set("limit", String(params.limit));
  }
  if (params.offset !== undefined) {
    query.set("offset", String(params.offset));
  }

  const response = await api.get<AuditLogFeedResponse>(`/history?${query.toString()}`);
  return response.data;
}

/**
 * Retrieves all Q&A conversation threads for the current user, optionally filtered by contract.
 */
export async function fetchConversations(params?: {
  contract_id?: number;
  limit?: number;
  offset?: number;
}): Promise<ConversationItem[]> {
  const query = new URLSearchParams();
  if (params?.contract_id) {
    query.set("contract_id", String(params.contract_id));
  }
  if (params?.limit) {
    query.set("limit", String(params.limit));
  }
  if (params?.offset !== undefined) {
    query.set("offset", String(params.offset));
  }

  const response = await api.get<ConversationItem[]>(`/conversations?${query.toString()}`);
  return response.data;
}

/**
 * Fetches the complete message history and cited clause references for a specific conversation.
 */
export async function fetchConversationDetail(conversationId: number): Promise<ConversationDetail> {
  const response = await api.get<ConversationDetail>(`/conversations/${conversationId}`);
  return response.data;
}

/**
 * Updates the title of an existing conversation thread.
 */
export async function updateConversationTitle(
  conversationId: number,
  title: string
): Promise<ConversationItem> {
  const response = await api.patch<ConversationItem>(`/conversations/${conversationId}`, {
    title,
  });
  return response.data;
}

/**
 * Deletes a conversation thread and all its messages.
 */
export async function deleteConversation(conversationId: number): Promise<void> {
  await api.delete(`/conversations/${conversationId}`);
}
