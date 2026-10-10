import type {
  AlertPreview,
  AlertRequest,
  AlertResponse,
  ErrorCode,
  Forecasts,
  Health,
  Model,
  Stock,
  Tickers,
} from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** `network_error` is client-only: the API could not be reached at all. */
export type ApiErrorCode = ErrorCode | "network_error";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: ApiErrorCode,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError(0, "network_error", "Can't reach the SentiFi API.");
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (body as { error?: { code?: ErrorCode; message?: string } } | null)?.error;
    throw new ApiError(
      response.status,
      error?.code ?? "internal_error",
      error?.message ?? `Request failed (${response.status})`,
    );
  }
  return body as T;
}

export const getHealth = () => request<Health>("/api/health");

export const getTickers = () => request<Tickers>("/api/tickers");

export const getStock = (symbol: string) => request<Stock>(`/api/stocks/${encodeURIComponent(symbol)}`);

export const getModel = () => request<Model>("/api/model");

export function getForecasts(params: { symbol?: string; limit?: number } = {}) {
  const query = new URLSearchParams();
  if (params.symbol) query.set("symbol", params.symbol);
  if (params.limit) query.set("limit", String(params.limit));
  const suffix = query.size ? `?${query}` : "";
  return request<Forecasts>(`/api/forecasts${suffix}`);
}

export const getAlertPreview = (symbol: string) =>
  request<AlertPreview>(`/api/alerts/preview?symbol=${encodeURIComponent(symbol)}`);

export const createAlert = (body: AlertRequest) =>
  request<AlertResponse>("/api/alerts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
