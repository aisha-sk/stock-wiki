"""SentiFi API. GET responses are the artifact files in DATA_DIR, unchanged."""

import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import errors, store
from .errors import DataUnavailable
from .schemas import ErrorBody, Forecasts, Health, Model, Stock, Tickers

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
