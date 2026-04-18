/**
 * Thin fetch wrapper that unwraps the ``ApiResponse`` envelope and surfaces
 * typed errors. All calls go through here — no ad-hoc ``fetch`` in components.
 */

import type { ApiError, ApiResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiRequestError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

function getToken(): string | undefined {
  if (typeof window === "undefined") {
    return process.env.API_TOKEN;
  }
  return (
    window.localStorage.getItem("e-state:token") ??
    process.env.NEXT_PUBLIC_DEMO_TOKEN ??
    undefined
  );
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token === null) window.localStorage.removeItem("e-state:token");
  else window.localStorage.setItem("e-state:token", token);
}

type Query = Record<string, string | number | boolean | undefined | null>;

function buildUrl(path: string, query?: Query): string {
  const url = new URL(path.startsWith("http") ? path : `${API_BASE}${path}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  form?: FormData;
  query?: Query;
  signal?: AbortSignal;
  anonymous?: boolean;
}

export async function apiFetch<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (!opts.form) headers["Content-Type"] = "application/json";
  if (!opts.anonymous) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(buildUrl(path, opts.query), {
    method: opts.method ?? "GET",
    headers,
    body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
    signal: opts.signal,
    cache: "no-store",
  });

  const payload = (await res.json().catch(() => null)) as
    | ApiResponse<T>
    | ApiError
    | null;
  if (!payload) {
    throw new ApiRequestError("INTERNAL", "Empty response", undefined, res.status);
  }
  if (payload.success) {
    return payload.data;
  }
  throw new ApiRequestError(
    payload.error.code,
    payload.error.message,
    payload.error.details,
    res.status,
  );
}
