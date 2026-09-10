/**
 * Centralized error classification for API/runtime failures.
 * -----------------------------------------------------------
 * Turns an arbitrary error (usually an Axios error) into a stable,
 * user-facing shape so every page and the ErrorBoundary render a
 * consistent custom error screen — without ever leaking another
 * tenant's data or tearing down the authenticated session.
 *
 * Security note: the backend enforces `user_id == current_user.id` on
 * every object route and returns 404 (never another user's data) when a
 * resource is not owned by the caller. So a 403/404 here means "not yours
 * / doesn't exist" — it is NOT an authentication failure and must never
 * trigger a logout. Only a genuine 401 (handled in services/api.ts) ends
 * the session.
 */

export type ErrorKind = "notfound" | "forbidden" | "server" | "network" | "unknown";

export interface ClassifiedError {
  kind: ErrorKind;
  /** HTTP-style code for display (e.g. 404, 403, 500, or "!" for network). */
  code: string;
  title: string;
  message: string;
  /** Raw backend detail, kept only for optional technical display. */
  detail?: string;
}

interface AxiosLikeError {
  response?: { status?: number; data?: { detail?: unknown } };
  message?: string;
  code?: string;
}

function extractDetail(err: AxiosLikeError): string | undefined {
  const d = err?.response?.data?.detail;
  if (typeof d === "string" && d.trim()) return d;
  return undefined;
}

/**
 * Classify any thrown value into a stable, safe, user-facing error shape.
 * `resourceLabel` tailors the copy (e.g. "contract", "conversation").
 */
export function classifyError(err: unknown, resourceLabel = "resource"): ClassifiedError {
  const e = (err ?? {}) as AxiosLikeError;
  const status = e?.response?.status;
  const detail = extractDetail(e);

  // No HTTP response at all → network / server unreachable.
  if (!status) {
    return {
      kind: "network",
      code: "!",
      title: "Connection Interrupted",
      message:
        "We couldn't reach the intelligence service. Check your connection and try again — your session is still active.",
      detail,
    };
  }

  if (status === 404) {
    return {
      kind: "notfound",
      code: "404",
      title: "Not Found",
      message: `This ${resourceLabel} doesn't exist, or it belongs to another account and isn't available to you.`,
      detail,
    };
  }

  if (status === 403) {
    return {
      kind: "forbidden",
      code: "403",
      title: "Access Denied",
      message: `You don't have permission to view this ${resourceLabel}. Documents and reports are private to the account that created them.`,
      detail,
    };
  }

  if (status >= 500) {
    return {
      kind: "server",
      code: String(status),
      title: "Something Went Wrong",
      message:
        "The service hit an unexpected error while processing your request. Please try again in a moment.",
      detail,
    };
  }

  // 400/409/422 and other client errors — show the backend message when safe.
  return {
    kind: "unknown",
    code: String(status),
    title: "Request Could Not Be Completed",
    message:
      detail ||
      "We couldn't complete that request. Please review your input and try again.",
    detail,
  };
}

/** Convenience: is this error one that means "not this user's data"? */
export function isOwnershipError(err: unknown): boolean {
  const status = (err as AxiosLikeError)?.response?.status;
  return status === 403 || status === 404;
}
