/**
 * Thin fetch wrapper that unwraps the ``ApiResponse`` envelope and surfaces
 * typed errors. All calls go through here — no ad-hoc ``fetch`` in components.
 */

import type { ApiError, ApiResponse, Meta } from "./types";

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

export interface ApiDataWithMeta<T> {
  data: T;
  meta?: Meta;
}

export interface DownloadResult {
  blob: Blob;
  filename: string | null;
}

async function requestEnvelope<T>(path: string, opts: RequestOptions = {}): Promise<ApiResponse<T>> {
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
    return payload;
  }
  throw new ApiRequestError(
    payload.error.code,
    payload.error.message,
    payload.error.details,
    res.status,
  );
}

export async function apiFetchWithMeta<T>(
  path: string,
  opts: RequestOptions = {},
): Promise<ApiDataWithMeta<T>> {
  const payload = await requestEnvelope<T>(path, opts);
  return { data: payload.data, meta: payload.meta };
}

export async function apiFetch<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const payload = await requestEnvelope<T>(path, opts);
  return payload.data;
}

export async function apiDownload(path: string, opts: RequestOptions = {}): Promise<DownloadResult> {
  const headers: Record<string, string> = {};
  if (!opts.anonymous) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(buildUrl(path, opts.query), {
    method: opts.method ?? "GET",
    headers,
    signal: opts.signal,
    cache: "no-store",
  });
  if (!res.ok) {
    const payload = (await res.json().catch(() => null)) as ApiError | null;
    if (payload && !payload.success) {
      throw new ApiRequestError(
        payload.error.code,
        payload.error.message,
        payload.error.details,
        res.status,
      );
    }
    throw new ApiRequestError("INTERNAL", "Download failed", undefined, res.status);
  }

  const disposition = res.headers.get("Content-Disposition");
  const match = disposition?.match(/filename="?([^"]+)"?/i);
  const filename = match?.[1] ?? null;
  return { blob: await res.blob(), filename };
}
