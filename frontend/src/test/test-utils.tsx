import React, { type ReactElement } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { MemoryRouter, type InitialEntry } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { User } from "../store/useAuthStore";

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

interface ExtendedRenderOptions extends Omit<RenderOptions, "queries"> {
  initialEntries?: InitialEntry[];
  queryClient?: QueryClient;
}

export function renderWithProviders(
  ui: ReactElement,
  {
    initialEntries = ["/"],
    queryClient = createTestQueryClient(),
    ...renderOptions
  }: ExtendedRenderOptions = {}
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  }

  return {
    ...render(ui, { wrapper: Wrapper, ...renderOptions }),
    queryClient,
  };
}

// Mock Data Factories
export const mockUser: User = {
  id: 1,
  email: "lawyer@example.com",
  is_active: true,
  is_2fa_enabled: false,
  created_at: "2026-09-01T00:00:00Z",
};

export const mockContract = {
  id: 42,
  filename: "Master_Services_Agreement.pdf",
  upload_path: "/uploads/user_1/Master_Services_Agreement.pdf",
  status: "analyzed" as const,
  created_at: "2026-09-05T14:30:00Z",
};

export const mockAnalysisData = {
  contract_id: 42,
  status: "completed",
  document_type: "Master Services Agreement (SaaS)",
  metadata: {
    party_a: "Acme Cloud Solutions Inc.",
    party_b: "Global Enterprises LLC",
    effective_date: "October 1, 2026",
    jurisdiction: "State of California",
    governing_law: "California, USA",
    financial_terms: "$50,000 annually payable net-30",
    liability_cap_status: "Limited to 12 months fees",
    termination_notice: "30 days written notice for cause",
  },
  clauses: {
    payment_terms: {
      text: "Customer shall pay invoices within thirty (30) days of receipt.",
      location: "Section 3.1",
      present: true,
    },
    termination_clauses: {
      text: "Either party may terminate for material breach with thirty (30) days written notice.",
      location: "Section 7.2",
      present: true,
    },
    liability_clauses: {
      text: "Neither party shall be liable for consequential damages. Aggregate liability capped at 12 months fees paid.",
      location: "Section 9.1",
      present: true,
    },
    confidentiality_clauses: {
      text: "Each party shall hold confidential information in strict confidence for 3 years.",
      location: "Section 5.1",
      present: true,
    },
    intellectual_property_clauses: {
      text: "Provider retains all proprietary rights in and to the SaaS service and documentation.",
      location: "Section 4.1",
      present: true,
    },
  },
  risks: [
    {
      risk_type: "Uncapped Consequential Damages Carve-Out",
      flag_category: "RED_FLAG" as const,
      severity: "RED_FLAG" as const,
      explanation: "Indemnification obligations are exempted from the aggregate liability cap, creating unlimited exposure.",
      clause_text: "The liability cap shall not apply to indemnification obligations under Section 10.",
      suggested_revision: "Cap indemnity claims at 2x annual contract value or a fixed amount.",
      irac_issue: "Is indemnity exposure uncapped?",
      irac_rule: "Standard commercial norm limits indemnity to insurance cover limits or 2x fees.",
      irac_analysis: "Exempting indemnity from the liability cap exposes the vendor to unlimited third-party damages.",
      irac_conclusion: "Uncapped liability poses severe financial risk.",
    },
    {
      risk_type: "Extended Non-Renewal Notice Period",
      flag_category: "YELLOW_FLAG" as const,
      severity: "YELLOW_FLAG" as const,
      explanation: "Auto-renewal requires 90 days advance notice to opt out instead of industry standard 30 days.",
      clause_text: "Notice of non-renewal must be delivered at least 90 days prior to term end.",
      suggested_revision: "Reduce non-renewal notice window to 30 days.",
    },
    {
      risk_type: "Standard Mutual Confidentiality Exceptions",
      flag_category: "GREEN_FLAG" as const,
      severity: "GREEN_FLAG" as const,
      explanation: "Contains standard 4-tier carve-outs for public domain, prior possession, independent development, and court order.",
      clause_text: "Confidentiality shall not apply to information generally known to the public.",
    },
  ],
  compliance_issues: [
    {
      statute: "DPDP Act 2023",
      domain: "Data Protection",
      issue_type: "Missing Data Protection Officer Contact",
      severity: "MEDIUM" as const,
      explanation: "The agreement processes Indian user data but fails to specify the contact details of the Data Protection Officer.",
      recommendation: "Insert DPO name, official email address, and grievance redressal timeline.",
    },
  ],
  summary: "Comprehensive SaaS agreement between Acme Cloud Solutions and Global Enterprises. Features balanced payment terms and intellectual property retention, with one high-risk uncapped indemnity clause.",
};

import type { AuditLogItem } from "../services/historyService";

export const mockAuditLogItems: AuditLogItem[] = [
  {
    id: 101,
    user_id: 1,
    action: "UPLOAD_DOCUMENT",
    category: "CONTRACTS",
    status: "SUCCESS",
    description: "Uploaded document Master_Services_Agreement.pdf",
    ip_address: "127.0.0.1",
    timestamp: "2026-09-08T10:00:00Z",
    metadata_json: { filename: "Master_Services_Agreement.pdf", file_size: 102400 },
  },
  {
    id: 102,
    user_id: 1,
    action: "RUN_ANALYSIS",
    category: "ANALYSIS",
    status: "SUCCESS",
    description: "Completed 5-agent LangGraph analysis for contract #42",
    ip_address: "127.0.0.1",
    timestamp: "2026-09-08T10:02:00Z",
    metadata_json: { contract_id: 42, risks_count: 3 },
  },
  {
    id: 103,
    user_id: 1,
    action: "USER_LOGIN",
    category: "AUTH",
    status: "SUCCESS",
    description: "User logged in successfully via email/password",
    ip_address: "127.0.0.1",
    timestamp: "2026-09-08T09:55:00Z",
    metadata_json: { auth_method: "password" },
  },
  {
    id: 104,
    user_id: 1,
    action: "ASK_QUESTION",
    category: "CHAT",
    status: "SUCCESS",
    description: "Asked legal query: 'Can I terminate early?'",
    ip_address: "127.0.0.1",
    timestamp: "2026-09-08T10:05:00Z",
    metadata_json: { contract_id: 42, question_length: 24 },
  },
];
