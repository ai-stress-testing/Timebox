import { z } from "zod";
import { use_session_store } from "../Store/session-store";

/*
 * The single fetch wrapper for the whole app.
 * - Relative base URL: Vite proxies /api -> http://localhost:8787 in dev.
 * - Injects the bearer token from the in-memory session store.
 * - 401 on an authenticated call locks the session (back to the vault).
 * - Every JSON body is validated with zod `.safeParse` before it is returned.
 */

const base_url = "/api/v1";

export type ApiErrorKind = "http" | "network" | "parse";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;

  constructor(kind: ApiErrorKind, message: string, status: number | null = null) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

export type ApiRequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
};

const detail_schema = z.object({ detail: z.string() });
const detail_list_schema = z.object({
  detail: z.array(z.object({ msg: z.string() }).passthrough()).min(1),
});

function build_headers(): Record<string, string> {
  const token = use_session_store.getState().token;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function run_fetch(
  path: string,
  options: ApiRequestOptions,
): Promise<Response> {
  const init: RequestInit = {
    method: options.method ?? "GET",
    headers: build_headers(),
  };
  if (options.body !== undefined) init.body = JSON.stringify(options.body);
  try {
    return await fetch(`${base_url}${path}`, init);
  } catch {
    throw new ApiError("network", "Cannot reach the Timebox API. Is it running?");
  }
}

async function extract_detail(response: Response): Promise<string> {
  const fallback = `Request failed (${response.status}).`;
  const payload: unknown = await response.json().catch(() => null);
  const as_string = detail_schema.safeParse(payload);
  if (as_string.success) return as_string.data.detail;
  const as_list = detail_list_schema.safeParse(payload);
  if (as_list.success) return as_list.data.detail.map((item) => item.msg).join("; ");
  return fallback;
}

async function ensure_ok(response: Response): Promise<void> {
  if (response.ok) return;
  const had_token = use_session_store.getState().token !== null;
  const is_unauthorized = response.status === 401;
  if (is_unauthorized && had_token) {
    use_session_store.getState().lock();
    throw new ApiError(
      "http",
      "Session expired — unlock again with your key file.",
      401,
    );
  }
  throw new ApiError("http", await extract_detail(response), response.status);
}

/** Request + validate: the only path any server data enters the app through. */
export async function api_request<T>(
  path: string,
  schema: z.ZodType<T>,
  options: ApiRequestOptions = {},
): Promise<T> {
  const response = await run_fetch(path, options);
  await ensure_ok(response);
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw new ApiError("parse", "The API returned malformed JSON.");
  }
  const parsed = schema.safeParse(payload);
  if (!parsed.success) {
    throw new ApiError(
      "parse",
      "The API response did not match the contract.",
    );
  }
  return parsed.data;
}

/** For 204-style endpoints (DELETE, /vault/lock, /vault/reset). */
export async function api_request_empty(
  path: string,
  options: ApiRequestOptions = {},
): Promise<void> {
  const response = await run_fetch(path, options);
  await ensure_ok(response);
}

export function to_error_message(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong.";
}

export function is_service_unavailable(error: unknown): boolean {
  return error instanceof ApiError && error.status === 503;
}

export function is_unauthorized(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}
