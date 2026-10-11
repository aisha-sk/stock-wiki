"""Pydantic mirrors of contracts/schemas/*.schema.json.

Used to validate artifact files before they are served and to document responses.
The JSON Schemas are the source of truth: change them first, then this file.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field

Symbol = Annotated[str, Field(pattern=r"^[A-Z][A-Z.]{0,5}$")]
Score = Annotated[int, Field(ge=-100, le=100)]
Source = Literal["analysts", "news", "reddit"]
Label = Literal["bullish", "neutral", "bearish"]
Direction = Literal["up", "down"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


# --- tickers.json ---------------------------------------------------------


class Ticker(Contract):
    symbol: Symbol
    name: str = Field(min_length=1)


class Tickers(Contract):
    schema_version: Literal["1.0"]
    tickers: list[Ticker] = Field(min_length=1)


# --- stocks/{SYMBOL}.json -------------------------------------------------


class Quote(Contract):
    price: float = Field(gt=0)
    change_pct: float
    as_of: date
    currency: Literal["USD"]


class PricePoint(Contract):
    date: date
    close: float = Field(gt=0)


class Forecast(Contract):
    horizon_days: Literal[5]
    direction: Direction
    prob_up: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0.5, le=1)
    made_at: AwareDatetime
    as_of_date: date
    target_date: date
    model_name: str
    model_version: str = Field(pattern=r"^[0-9]+$")


class SentimentSource(Contract):
    source: Source
    display_name: str
    score: Score
    label: Label
    doc_count: int = Field(ge=0)
    note: str
    method: Literal["finbert", "llm", "ratings"]
    previous_score: Score | None


class Gap(Contract):
    points: int = Field(ge=0, le=200)
    most_bullish: Source
    most_bearish: Source
    summary: str


class Sentiment(Contract):
    window_days: int = Field(ge=1)
    sources: list[SentimentSource] = Field(max_length=3)
    gap: Gap | None


class Headline(Contract):
    id: str = Field(min_length=1)
    source: Source
    publisher: str
    title: str = Field(min_length=1)
    url: str | None
    published_at: AwareDatetime
    score: Score
    label: Label


class Stock(Contract):
    schema_version: Literal["1.0"]
    symbol: Symbol
    name: str = Field(min_length=1)
    generated_at: AwareDatetime
    is_demo_data: bool
    quote: Quote
    prices: list[PricePoint] = Field(min_length=20, max_length=260)
    forecast: Forecast | None
    sentiment: Sentiment
    headlines: list[Headline] = Field(max_length=30)


# --- API-only shapes ------------------------------------------------------


class Health(Contract):
    status: Literal["ok"]
    api_version: Literal["1.0"]
    data_generated_at: AwareDatetime | None
    is_demo_data: bool


ErrorCode = Literal["not_found", "validation_error", "data_unavailable", "internal_error"]


class ErrorDetail(Contract):
    code: ErrorCode
    message: str


class ErrorBody(Contract):
    error: ErrorDetail


# --- model.json -----------------------------------------------------------

Rate = Annotated[float, Field(ge=0, le=1)]
Version = Annotated[str, Field(pattern=r"^[0-9]+$")]
Algorithm = Literal["logistic_regression", "xgboost"]


class ProductionModel(Contract):
    model_name: str
    version: Version
    algorithm: Algorithm
    trained_at: AwareDatetime


class ModelTask(Contract):
    description: str
    horizon_days: Literal[5]
    validation: Literal["walk_forward", "chronological_holdout"]
    tickers: list[str] = Field(min_length=1)
    test_start: date
    test_end: date
    n_test: int = Field(ge=1)


class ModelMetrics(Contract):
    directional_accuracy: Rate
    precision: Rate
    recall: Rate
    f1: Rate
    sharpe_ratio: float | None
    max_drawdown: Annotated[float, Field(le=0)] | None
    inference_latency_ms: Annotated[float, Field(ge=0)] | None
    cost_per_request_usd: Annotated[float, Field(ge=0)] | None


class Baseline(Contract):
    name: Literal["always_up", "previous_direction"]
    directional_accuracy: Rate


class Gate(Contract):
    metric: Literal["directional_accuracy"]
    threshold: Rate
    passed: bool


class WeeklyAccuracy(Contract):
    week_start: date
    accuracy: Rate
    n: int = Field(ge=1)


class ModelVersion(Contract):
    version: Version
    model_name: str
    algorithm: Algorithm
    trained_at: AwareDatetime
    directional_accuracy: Rate
    gate_passed: bool
    status: Literal["production", "archived", "rejected"]
    mlflow_run_id: str | None


class Model(Contract):
    schema_version: Literal["1.0"]
    generated_at: AwareDatetime
    is_demo_data: bool
    production: ProductionModel | None
    task: ModelTask
    metrics: ModelMetrics
    baselines: list[Baseline]
    gate: Gate
    weekly_accuracy: list[WeeklyAccuracy] = Field(max_length=12)
    versions: list[ModelVersion]


# --- forecasts.json -------------------------------------------------------


class ForecastSummary(Contract):
    resolved: int = Field(ge=0)
    hits: int = Field(ge=0)
    hit_rate: Rate | None
    pending: int = Field(ge=0)


class ForecastRow(Contract):
    id: str
    symbol: Symbol
    made_at: AwareDatetime
    as_of_date: date
    target_date: date
    horizon_days: Literal[5]
    direction: Direction
    prob_up: Rate
    model_version: Version
    origin: Literal["backtest", "live"]
    status: Literal["pending", "resolved"]
    actual_direction: Direction | None
    actual_return_pct: float | None
    result: Literal["hit", "miss"] | None


class Forecasts(Contract):
    schema_version: Literal["1.0"]
    generated_at: AwareDatetime
    is_demo_data: bool
    summary: ForecastSummary
    forecasts: list[ForecastRow]


# --- alerts ---------------------------------------------------------------

AlertTrigger = Literal["sharp_shift", "any_flip", "weekly_digest"]


class AlertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    symbol: str = Field(min_length=1, max_length=6)
    trigger: AlertTrigger


class AlertResponse(Contract):
    id: str
    email: str
    symbol: str
    trigger: AlertTrigger
    created_at: AwareDatetime
    delivery: Literal["mock", "email"]


class AlertPreview(Contract):
    symbol: str
    subject: str
    body_lines: list[str]
    is_demo_data: bool


# --- explain (optional, needs an Anthropic credential on the server) -----


class ExplainRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1, max_length=6)
    question: str = Field(min_length=1, max_length=500)


class Citation(Contract):
    headline_id: str
    title: str
    url: str | None


class ExplainResponse(Contract):
    symbol: str
    answer: str
    citations: list[Citation]
    model: str
    generated_at: AwareDatetime
