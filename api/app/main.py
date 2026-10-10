"""SentiFi API. GET responses are the artifact files in DATA_DIR, unchanged."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import errors, store
from .errors import DataUnavailable
from .schemas import ErrorBody, Health, Stock, Tickers

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
