import { ApiProblemError, type ApiProblem } from "@/lib/api/contracts";
import type { DataEnvelope, ProblemDetails } from "@/lib/api/backend-contracts";

export interface ApiHttpClientOptions {
  baseUrl?: string;
  fetch?: typeof globalThis.fetch;
  credentials?: RequestCredentials;
  defaultHeaders?: () => HeadersInit | Promise<HeadersInit>;
  origin?: string;
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  organizationId?: string;
  query?: Record<
    string,
    | string
    | number
    | boolean
    | ReadonlyArray<string | number | boolean>
    | undefined
    | null
  >;
  json?: unknown;
  body?: BodyInit;
  headers?: HeadersInit;
  ifMatch?: string;
  idempotent?: boolean;
  idempotencyKey?: string;
  signal?: AbortSignal;
  csrfRetry?: boolean;
}

export interface ApiResponse<T> {
  data: T;
  etag: string | null;
  location: string | null;
  idempotencyReplayed: boolean;
}

export interface DownloadArtifact {
  blob: Blob;
  filename: string | null;
  contentType: string;
}

const mutatingMethods = new Set(["POST", "PATCH", "DELETE"]);

function requestUrl(
  baseUrl: string,
  path: string,
  query?: ApiRequestOptions["query"]
): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${baseUrl}${normalizedPath}`;
  if (!query) return url;

  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      if (item !== undefined && item !== null && item !== "") {
        search.append(key, String(item));
      }
    }
  }
  const serialized = search.toString();
  return serialized ? `${url}?${serialized}` : url;
}

function fallbackProblem(response: Response): ProblemDetails {
  return {
    type: "about:blank",
    title: response.statusText || "Request failed",
    status: response.status,
    detail: "The server could not complete this request.",
    instance: response.url,
    code: "request_failed",
    request_id: response.headers.get("X-Request-ID") ?? "unknown"
  };
}

function toApiProblem(problem: ProblemDetails): ApiProblem {
  return {
    type: problem.type,
    title: problem.title,
    detail: problem.detail,
    status: problem.status,
    code: problem.code,
    instance: problem.instance,
    request_id: problem.request_id,
    errors: problem.errors
  };
}

async function problemFrom(response: Response): Promise<ProblemDetails> {
  const contentType = response.headers.get("Content-Type") ?? "";
  if (contentType.includes("json")) {
    try {
      const value = (await response.json()) as Partial<ProblemDetails>;
      const fallback = fallbackProblem(response);
      return {
        ...fallback,
        ...value,
        status: response.status,
        errors: Array.isArray(value.errors) ? value.errors : undefined
      };
    } catch {
      return fallbackProblem(response);
    }
  }
  return fallbackProblem(response);
}

function contentDispositionFilename(value: string | null): string | null {
  if (!value) return null;
  const encoded = value.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  if (encoded) {
    try {
      return decodeURIComponent(encoded);
    } catch {
      return encoded;
    }
  }
  return value.match(/filename="?([^";]+)"?/i)?.[1] ?? null;
}

export function createIdempotencyKey(): string {
  return globalThis.crypto.randomUUID();
}

export async function sha256Hex(value: Blob): Promise<string> {
  const bytes = await value.arrayBuffer();
  const digest = await globalThis.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0")
  ).join("");
}

export class ApiHttpClient {
  private readonly baseUrl: string;
  private readonly fetcher: typeof globalThis.fetch;
  private readonly credentials: RequestCredentials;
  private readonly defaultHeaders?: ApiHttpClientOptions["defaultHeaders"];
  private readonly origin?: string;
  private csrfToken: string | null = null;
  private csrfRequest: Promise<string> | null = null;

  constructor(options: ApiHttpClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? "/api/v1").replace(/\/$/, "");
    this.fetcher = options.fetch ?? globalThis.fetch.bind(globalThis);
    this.credentials = options.credentials ?? "include";
    this.defaultHeaders = options.defaultHeaders;
    this.origin = options.origin;
  }

  clearCsrfToken(): void {
    this.csrfToken = null;
  }

  async refreshCsrfToken(signal?: AbortSignal): Promise<string> {
    this.csrfToken = null;
    return this.getCsrfToken(signal);
  }

  async getCsrfToken(signal?: AbortSignal): Promise<string> {
    if (this.csrfToken) return this.csrfToken;
    if (this.csrfRequest) return this.csrfRequest;

    this.csrfRequest = (async () => {
      const headers = new Headers(await this.defaultHeaders?.());
      headers.set("Accept", "application/json");
      const response = await this.fetcher(
        requestUrl(this.baseUrl, "/auth/csrf-token"),
        {
          method: "GET",
          headers,
          credentials: this.credentials,
          cache: "no-store",
          signal
        }
      );
      if (!response.ok) {
        throw new ApiProblemError(toApiProblem(await problemFrom(response)));
      }
      const envelope = (await response.json()) as DataEnvelope<{
        csrf_token: string;
      }>;
      this.csrfToken = envelope.data.csrf_token;
      return envelope.data.csrf_token;
    })();

    try {
      return await this.csrfRequest;
    } finally {
      this.csrfRequest = null;
    }
  }

  async request<T>(
    path: string,
    options: ApiRequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const method = options.method ?? "GET";
    const mutating = mutatingMethods.has(method);
    const headers = new Headers(await this.defaultHeaders?.());
    new Headers(options.headers).forEach((value, key) =>
      headers.set(key, value)
    );
    headers.set("Accept", "application/json");

    if (options.organizationId) {
      headers.set("X-Organization-ID", options.organizationId);
    }
    if (options.ifMatch) headers.set("If-Match", options.ifMatch);
    const idempotencyKey = options.idempotent
      ? (options.idempotencyKey ?? createIdempotencyKey())
      : options.idempotencyKey;
    if (idempotencyKey) {
      headers.set("Idempotency-Key", idempotencyKey);
    }
    if (mutating) {
      headers.set("X-CSRF-Token", await this.getCsrfToken(options.signal));
      if (this.origin) headers.set("Origin", this.origin);
    }

    let body = options.body;
    if (options.json !== undefined) {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(options.json);
    }

    const response = await this.fetcher(
      requestUrl(this.baseUrl, path, options.query),
      {
        method,
        body,
        headers,
        credentials: this.credentials,
        cache: "no-store",
        signal: options.signal
      }
    );

    if (!response.ok) {
      const problem = await problemFrom(response);
      if (
        mutating &&
        options.csrfRetry !== false &&
        (problem.code === "csrf_failed" ||
          problem.code === "csrf_token_invalid")
      ) {
        await this.refreshCsrfToken(options.signal);
        return this.request<T>(path, {
          ...options,
          idempotencyKey,
          csrfRetry: false
        });
      }
      throw new ApiProblemError(toApiProblem(problem));
    }

    const data =
      response.status === 204
        ? (undefined as T)
        : ((await response.json()) as DataEnvelope<T>).data;
    return {
      data,
      etag: response.headers.get("ETag"),
      location: response.headers.get("Location"),
      idempotencyReplayed:
        response.headers.get("Idempotency-Replayed") === "true"
    };
  }

  async collection<T>(
    path: string,
    options: ApiRequestOptions = {}
  ): Promise<import("@/lib/api/backend-contracts").CollectionEnvelope<T>> {
    const method = options.method ?? "GET";
    const headers = new Headers(await this.defaultHeaders?.());
    new Headers(options.headers).forEach((value, key) =>
      headers.set(key, value)
    );
    headers.set("Accept", "application/json");
    if (options.organizationId) {
      headers.set("X-Organization-ID", options.organizationId);
    }
    const response = await this.fetcher(
      requestUrl(this.baseUrl, path, options.query),
      {
        method,
        headers,
        credentials: this.credentials,
        cache: "no-store",
        signal: options.signal
      }
    );
    if (!response.ok) {
      throw new ApiProblemError(toApiProblem(await problemFrom(response)));
    }
    return (await response.json()) as import("@/lib/api/backend-contracts").CollectionEnvelope<T>;
  }

  async download(
    path: string,
    options: ApiRequestOptions = {}
  ): Promise<DownloadArtifact> {
    const headers = new Headers(await this.defaultHeaders?.());
    new Headers(options.headers).forEach((value, key) =>
      headers.set(key, value)
    );
    if (options.organizationId) {
      headers.set("X-Organization-ID", options.organizationId);
    }
    const response = await this.fetcher(
      requestUrl(this.baseUrl, path, options.query),
      {
        method: "GET",
        headers,
        credentials: this.credentials,
        cache: "no-store",
        signal: options.signal
      }
    );
    if (!response.ok) {
      throw new ApiProblemError(toApiProblem(await problemFrom(response)));
    }
    return {
      blob: await response.blob(),
      filename: contentDispositionFilename(
        response.headers.get("Content-Disposition")
      ),
      contentType:
        response.headers.get("Content-Type") ?? "application/octet-stream"
    };
  }
}

export interface PollOptions<T> {
  signal?: AbortSignal;
  intervalMs?: number;
  isComplete: (value: T) => boolean;
  isFailed?: (value: T) => boolean;
}

export async function pollUntil<T>(
  load: (signal?: AbortSignal) => Promise<T>,
  options: PollOptions<T>
): Promise<T> {
  const intervalMs = options.intervalMs ?? 1_000;
  for (;;) {
    const value = await load(options.signal);
    if (options.isComplete(value)) return value;
    if (options.isFailed?.(value)) return value;
    await new Promise<void>((resolve, reject) => {
      const finish = () => {
        options.signal?.removeEventListener("abort", abort);
        resolve();
      };
      const timer = globalThis.setTimeout(finish, intervalMs);
      const abort = () => {
        globalThis.clearTimeout(timer);
        options.signal?.removeEventListener("abort", abort);
        reject(
          options.signal?.reason ?? new DOMException("Aborted", "AbortError")
        );
      };
      if (options.signal?.aborted) abort();
      else options.signal?.addEventListener("abort", abort, { once: true });
    });
  }
}
