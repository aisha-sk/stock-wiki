"""Read-only lookups over StockSense's published artifacts.

These are the tools both the MCP server and the explain agent expose. Each returns a trimmed
copy of what is in DATA_DIR. Nothing is computed here, so an agent cannot get a number from
these tools that the dashboard does not also show.
"""

import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = "contracts/examples"


class LookupFailed(Exception):
    """A readable problem to hand back to the caller, such as an unknown symbol."""


def _data_dir() -> Path:
    path = Path(os.environ.get("DATA_DIR") or DEFAULT_DATA_DIR)
    return path if path.is_absolute() else REPO_ROOT / path


def _read(relative: str) -> dict[str, Any]:
    try:
        return json.loads((_data_dir() / relative).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        raise LookupFailed(f"{relative} is not available") from None


def _stock(symbol: str) -> dict[str, Any]:
    symbol = symbol.strip().upper()
    tracked = [t["symbol"] for t in _read("tickers.json")["tickers"]]
    if symbol not in tracked:
        raise LookupFailed(f"Unknown symbol: {symbol}. Tracked symbols: {', '.join(tracked)}")
    return _read(f"stocks/{symbol}.json")


def list_tickers() -> list[dict[str, str]]:
    """The stocks StockSense tracks, as symbol and company name."""
    return _read("tickers.json")["tickers"]


def get_sentiment(symbol: str) -> dict[str, Any]:
    """Each group's sentiment score for one stock, from -100 (bearish) to 100 (bullish), and the gap.

    `previous_score` is the same group's score in the window before this one.
    `method` "ratings" means the score comes from analyst buy/hold/sell counts, not from text.
    """
    stock = _stock(symbol)
    return {
        "symbol": stock["symbol"],
        "name": stock["name"],
        "as_of": stock["generated_at"],
        "window_days": stock["sentiment"]["window_days"],
        "sources": stock["sentiment"]["sources"],
        "gap": stock["sentiment"]["gap"],
    }


def get_headlines(symbol: str, source: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """Recent scored headlines for one stock, newest first.

    `source` filters to "analysts", "news" or "reddit". Every headline has an `id` to cite it by.
    """
    headlines = _stock(symbol)["headlines"]
    if source is not None:
        if source not in {"analysts", "news", "reddit"}:
            raise LookupFailed('source must be "analysts", "news" or "reddit"')
        headlines = [h for h in headlines if h["source"] == source]
    return headlines[: max(1, min(limit, 30))]


def get_forecast(symbol: str) -> dict[str, Any]:
    """The model's 5-day large-versus-quiet move forecast for one stock, or why there is none."""
    stock = _stock(symbol)
    if stock["forecast"] is None:
        return {
            "symbol": stock["symbol"],
            "forecast": None,
            "reason": "No model version has passed the quality gate, so no forecast is served.",
        }
    return {"symbol": stock["symbol"], "forecast": stock["forecast"]}


def get_track_record(symbol: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Past forecasts beside what happened: hit, miss or pending.

    `origin` "backtest" rows are out-of-sample test predictions; "live" rows were logged before
    the outcome existed. Pass a symbol to see one stock only.
    """
    rows = _read("forecasts.json")["forecasts"]
    if symbol is not None:
        symbol = _stock(symbol)["symbol"]
        rows = [r for r in rows if r["symbol"] == symbol]
    resolved = [r for r in rows if r["status"] == "resolved"]
    hits = sum(r["result"] == "hit" for r in resolved)
    return {
        "summary": {
            "resolved": len(resolved),
            "hits": hits,
            "hit_rate": round(hits / len(resolved), 3) if resolved else None,
            "pending": len(rows) - len(resolved),
        },
        "forecasts": rows[: max(1, min(limit, 200))],
    }


def get_model_card() -> dict[str, Any]:
    """How the forecasting model is doing: metrics, baselines, the quality gate and every version."""
    model = _read("model.json")
    return {
        key: model[key]
        for key in ("generated_at", "production", "task", "metrics", "baselines", "gate", "versions")
    }
