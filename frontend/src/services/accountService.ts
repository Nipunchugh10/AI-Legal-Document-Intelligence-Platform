/**
 * Account Service
 * ---------------
 * API client methods and TypeScript interfaces for:
 * - Data portability (full account JSON export)
 * - User-configurable audit log retention policy
 * - Account deletion with dual-factor verification (Password + Email OTP)
 *
 * Day 48 — History Privacy, Retention, and Data Export
 */

import api from "./api";

export interface RetentionPolicyResponse {
  data_retention_days: number | null;
  allowed_options: (number | null)[];
}

export interface RetentionUpdateResponse {
  data_retention_days: number | null;
  message: string;
  purged_logs_count: number;
}

export interface AccountDeleteOTPResponse {
  message: string;
  expires_in_minutes: number;
}

export interface AccountDeleteResponse {
  message: string;
  deleted_at: string;
}

/**
 * Downloads the full account JSON export archive.
 * Initiates a browser file download using a temporary anchor element.
 */
export async function downloadAccountExport(): Promise<void> {
  const response = await api.get("/account/export", {
    responseType: "blob",
  });

  // Extract filename from Content-Disposition header if available
  let filename = `legal_ai_export_${new Date().toISOString().slice(0, 10)}.json`;
  const disposition = response.headers["content-disposition"];
  if (disposition) {
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1];
    }
  }

  const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/json" }));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute("download", filename);
  document.body.appendChild(link);
  link.click();
  link.parentNode?.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Retrieves the current data retention policy.
 */
export async function getRetentionPolicy(): Promise<RetentionPolicyResponse> {
  const response = await api.get<RetentionPolicyResponse>("/account/retention");
  return response.data;
}

/**
 * Updates the data retention policy.
 */
export async function updateRetentionPolicy(days: number | null): Promise<RetentionUpdateResponse> {
  const response = await api.patch<RetentionUpdateResponse>("/account/retention", {
    data_retention_days: days,
  });
  return response.data;
}

/**
 * Dispatches an email OTP for confirming account deletion.
 */
export async function requestAccountDeletionOTP(): Promise<AccountDeleteOTPResponse> {
  const response = await api.post<AccountDeleteOTPResponse>("/account/delete-otp");
  return response.data;
}

/**
 * Permanently deletes the account after verifying password and email OTP.
 */
export async function deleteAccount(password: string, otpCode: string): Promise<AccountDeleteResponse> {
  const response = await api.delete<AccountDeleteResponse>("/account", {
    data: {
      password,
      otp_code: otpCode,
    },
  });
  return response.data;
}
