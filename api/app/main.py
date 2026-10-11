"""SentiFi API. GET responses are the artifact files in DATA_DIR, unchanged."""

import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import alerts, errors, explainer, store
from .errors import DataUnavailable
from .schemas import (
    AlertPreview,
    AlertRequest,
    AlertResponse,
    ErrorBody,
    ExplainRequest,
    ExplainResponse,
    Forecasts,
    Health,
    Model,
    Stock,
    Tickers,
)

load_dotenv(store.REPO_ROOT / ".env")

API_VERSION = "1.0"

app = FastAPI(title="SentiFi API", version=API_VERSION)
errors.install(app)

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in origins if o],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

NOT_FOUND = {404: {"model": ErrorBody}}
UNAVAILABLE = {503: {"model": ErrorBody}}
INVALID = {422: {"model": ErrorBody}}


@app.get("/api/health", response_model=Health)
def health() -> JSONResponse:
    try:
        model = store.read_json("model.json")
    except DataUnavailable:
        model = {}
    return JSONResponse(
        {
            "status": "ok",
            "api_version": API_VERSION,
            "data_generated_at": model.get("generated_at"),
            "is_demo_data": bool(model.get("is_demo_data", False)),
        }
    )


@app.get("/api/tickers", response_model=Tickers, responses=UNAVAILABLE)
def get_tickers() -> JSONResponse:
    return JSONResponse(store.tickers())


@app.get("/api/stocks/{symbol}", response_model=Stock, responses=NOT_FOUND | UNAVAILABLE)
def get_stock(symbol: str) -> JSONResponse:
    return JSONResponse(store.stock(symbol))


@app.get("/api/model", response_model=Model, responses=UNAVAILABLE)
def get_model() -> JSONResponse:
    return JSONResponse(store.model())


@app.get("/api/forecasts", response_model=Forecasts, responses=NOT_FOUND | INVALID | UNAVAILABLE)
def get_forecasts(
    symbol: str | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> JSONResponse:
    return JSONResponse(store.forecasts(symbol, limit))


@app.post(
    "/api/alerts",
    response_model=AlertResponse,
    status_code=201,
    responses={200: {"model": AlertResponse}} | NOT_FOUND | INVALID,
)
def create_alert(body: AlertRequest) -> JSONResponse:
    symbol = store.known_symbol(body.symbol)
    alert, created = alerts.create(body.email, symbol, body.trigger)
    # The same email, symbol and trigger again returns the existing sign-up.
    return JSONResponse(alert, status_code=201 if created else 200)


@app.get("/api/alerts/preview", response_model=AlertPreview, responses=NOT_FOUND | INVALID | UNAVAILABLE)
def get_alert_preview(symbol: str) -> JSONResponse:
    return JSONResponse(alerts.preview(store.stock(symbol)))


@app.post("/api/explain", response_model=ExplainResponse, responses=NOT_FOUND | INVALID | UNAVAILABLE)
def explain(body: ExplainRequest) -> JSONResponse:
    stock = store.stock(body.symbol)
    return JSONResponse(explainer.answer(stock["symbol"], body.question.strip(), stock["generated_at"]))
