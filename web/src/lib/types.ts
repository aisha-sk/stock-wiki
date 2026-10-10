// Mirrors contracts/schemas/*.schema.json. Change the schema first, then this file.

export type Direction = "up" | "down";
export type Source = "analysts" | "news" | "reddit";
export type Label = "bullish" | "neutral" | "bearish";

// --- tickers.json ---

export interface Ticker {
  symbol: string;
  name: string;
}

export interface Tickers {
  schema_version: "1.0";
  tickers: Ticker[];
}

// --- stocks/{SYMBOL}.json ---

export interface Quote {
  price: number;
  /** Percent units: 1.8 means +1.8%. */
  change_pct: number;
  as_of: string;
  currency: "USD";
}

export interface PricePoint {
  date: string;
  close: number;
}

export interface Forecast {
  horizon_days: 5;
  direction: Direction;
  /** Fraction, 0 to 1. */
  prob_up: number;
  /** Fraction, 0.5 to 1. */
  confidence: number;
  made_at: string;
  as_of_date: string;
  target_date: string;
  model_name: string;
  model_version: string;
}

export interface SentimentSource {
  source: Source;
  display_name: string;
  /** Integer, -100 to 100. */
  score: number;
  label: Label;
  doc_count: number;
  note: string;
  method: "finbert" | "llm" | "ratings";
  previous_score: number | null;
}

export interface Gap {
  points: number;
  most_bullish: Source;
  most_bearish: Source;
  summary: string;
}

export interface Sentiment {
  window_days: number;
  /** 0 to 3 items, ordered analysts, news, reddit. */
  sources: SentimentSource[];
  gap: Gap | null;
}

export interface Headline {
  id: string;
  source: Source;
  publisher: string;
  title: string;
  url: string | null;
  published_at: string;
  score: number;
  label: Label;
}

export interface Stock {
  schema_version: "1.0";
  symbol: string;
  name: string;
  generated_at: string;
  is_demo_data: boolean;
  quote: Quote;
  prices: PricePoint[];
  forecast: Forecast | null;
  sentiment: Sentiment;
  headlines: Headline[];
}

// --- model.json ---

export type Algorithm = "logistic_regression" | "xgboost";
export type VersionStatus = "production" | "archived" | "rejected";

export interface ProductionModel {
  model_name: string;
  version: string;
  algorithm: Algorithm;
  trained_at: string;
}

export interface ModelTask {
  description: string;
  horizon_days: 5;
  validation: "walk_forward" | "chronological_holdout";
  tickers: string[];
  test_start: string;
  test_end: string;
  n_test: number;
}

/** Rates are fractions, 0 to 1. */
export interface ModelMetrics {
  directional_accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  sharpe_ratio: number | null;
  /** Negative fraction: -0.087 means -8.7%. */
  max_drawdown: number | null;
  inference_latency_ms: number | null;
  cost_per_request_usd: number | null;
}

export interface Baseline {
  name: "always_up" | "previous_direction";
  directional_accuracy: number;
}

export interface Gate {
  metric: "directional_accuracy";
  threshold: number;
  passed: boolean;
}

export interface WeeklyAccuracy {
  week_start: string;
  accuracy: number;
  n: number;
}

export interface ModelVersion {
  version: string;
  model_name: string;
  algorithm: Algorithm;
  trained_at: string;
  directional_accuracy: number;
  gate_passed: boolean;
  status: VersionStatus;
  mlflow_run_id: string | null;
}

export interface Model {
  schema_version: "1.0";
  generated_at: string;
  is_demo_data: boolean;
  production: ProductionModel | null;
  task: ModelTask;
  metrics: ModelMetrics;
  baselines: Baseline[];
  gate: Gate;
  weekly_accuracy: WeeklyAccuracy[];
  versions: ModelVersion[];
}

// --- forecasts.json ---

export interface ForecastRow {
  id: string;
  symbol: string;
  made_at: string;
  as_of_date: string;
  target_date: string;
  horizon_days: 5;
  direction: Direction;
  prob_up: number;
  model_version: string;
  origin: "backtest" | "live";
  status: "pending" | "resolved";
  actual_direction: Direction | null;
  /** Percent units: 3.1 means +3.1%. */
  actual_return_pct: number | null;
  result: "hit" | "miss" | null;
}

export interface ForecastSummary {
  resolved: number;
  hits: number;
  hit_rate: number | null;
  pending: number;
}

export interface Forecasts {
  schema_version: "1.0";
  generated_at: string;
  is_demo_data: boolean;
  summary: ForecastSummary;
  forecasts: ForecastRow[];
}

// --- API-only shapes ---

export interface Health {
  status: "ok";
  api_version: "1.0";
  data_generated_at: string | null;
  is_demo_data: boolean;
}

export type ErrorCode = "not_found" | "validation_error" | "data_unavailable" | "internal_error";

export interface ErrorBody {
  error: { code: ErrorCode; message: string };
}

export type AlertTrigger = "sharp_shift" | "any_flip" | "weekly_digest";

export interface AlertRequest {
  email: string;
  symbol: string;
  trigger: AlertTrigger;
}

export interface AlertResponse extends AlertRequest {
  id: string;
  created_at: string;
  delivery: "mock" | "email";
}

export interface AlertPreview {
  symbol: string;
  subject: string;
  body_lines: string[];
  is_demo_data: boolean;
}
