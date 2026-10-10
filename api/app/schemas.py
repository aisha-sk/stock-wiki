"""Pydantic mirrors of contracts/schemas/*.schema.json.

Used to validate artifact files before they are served and to document responses.
The JSON Schemas are the source of truth: change them first, then this file.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

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
