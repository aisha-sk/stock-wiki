"""Turn prices, a walk-forward result and scored headlines into contract JSON."""

import json
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

MODEL_NAME = "direction-xgb"
MODEL_VERSION = "1"
ALGORITHM = "xgboost"
TASK_DESCRIPTION = "Will the close 5 trading days from now be above today's close?"
HEADLINE_LIMIT = 30
FORECAST_LOG_LIMIT = 60


def nyse_sessions_after(as_of: str, sessions: int) -> str:
    """The date ``sessions`` completed NYSE sessions after ``as_of``."""
    start = pd.Timestamp(as_of).date()
    calendar = mcal.get_calendar("XNYS")
    schedule = calendar.schedule(
        start_date=start + pd.Timedelta(days=1),
        end_date=start + pd.Timedelta(days=sessions * 4 + 14),
    )
    future = [pd.Timestamp(day).date() for day in schedule.index]
    if len(future) < sessions:
        raise RuntimeError(f"not enough NYSE sessions after {as_of}")
    return future[sessions - 1].isoformat()


def session_close_z(as_of: str) -> str:
    """Official NYSE close of ``as_of``, in UTC with a Z suffix."""
    calendar = mcal.get_calendar("XNYS")
    schedule = calendar.schedule(start_date=as_of, end_date=as_of)
    if schedule.empty:
        return f"{as_of}T21:00:00Z"
    close = pd.Timestamp(schedule.iloc[0]["market_close"]).tz_convert("UTC")
    return close.strftime("%Y-%m-%dT%H:%M:%SZ")


def median_latency_ms(predict_one: Callable[[], object], repeats: int = 100) -> float:
    """Median milliseconds of ``repeats`` single-row predictions."""
    samples: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        predict_one()
        samples.append((time.perf_counter() - started) * 1000.0)
    return float(np.median(samples))


def build_weekly_accuracy(predictions: pd.DataFrame) -> list[dict]:
    """Accuracy by the Monday of each out-of-sample ``as_of_date``. Last 12 weeks."""
    frame = predictions.copy()
    frame["as_of_date"] = pd.to_datetime(frame["as_of_date"])
    frame["week_start"] = frame["as_of_date"] - pd.to_timedelta(
        frame["as_of_date"].dt.dayofweek, unit="D"
    )
    predicted_up = frame["prob_up"] >= 0.5
    actually_up = frame["y_true"].astype(int) == 1
    frame["correct"] = predicted_up == actually_up
    weeks: list[dict] = []
    for week_start, group in frame.groupby("week_start", sort=True):
        weeks.append(
            {
                "week_start": pd.Timestamp(week_start).strftime("%Y-%m-%d"),
                "accuracy": round(float(group["correct"].mean()), 4),
                "n": len(group),
            }
        )
    return weeks[-12:]


def build_stock(
    *,
    symbol: str,
    name: str,
    prices: pd.DataFrame,
    prices_in_payload: int,
    forecast_prob: float,
    gate_passed: bool,
    generated_at: str,
    window_days: int,
    source: dict | None,
    headlines: list[dict],
    model_name: str = MODEL_NAME,
    model_version: str = MODEL_VERSION,
) -> dict:
    """One ``stocks/{SYMBOL}.json`` body. Forecast is null when the gate failed."""
    ordered = prices.sort_values("date")
    window = ordered.tail(prices_in_payload)
    last = round(float(window["close"].iloc[-1]), 2)
    previous = round(float(window["close"].iloc[-2]), 2)
    as_of = _date(window["date"].iloc[-1])
    forecast = None
    if gate_passed:
        probability = round(float(forecast_prob), 4)
        forecast = {
            "horizon_days": 5,
            "direction": _direction(probability),
            "prob_up": probability,
            "confidence": float(max(probability, 1.0 - probability)),
            "made_at": generated_at,
            "as_of_date": as_of,
            "target_date": nyse_sessions_after(as_of, 5),
            "model_name": model_name,
            "model_version": model_version,
        }
    return {
        "schema_version": "1.0",
        "symbol": symbol,
        "name": name,
        "generated_at": generated_at,
        "is_demo_data": False,
        "quote": {
            "price": last,
            "change_pct": round((last / previous - 1.0) * 100.0, 2),
            "as_of": as_of,
            "currency": "USD",
        },
        "prices": [
            {"date": _date(row.date), "close": round(float(row.close), 2)}
            for row in window.itertuples(index=False)
        ],
        "forecast": forecast,
        "sentiment": {
            "window_days": window_days,
            "sources": [] if source is None else [source],
            "gap": None,
        },
        "headlines": _headlines(headlines),
    }


def build_forecast_rows(
    *,
    predictions: pd.DataFrame,
    symbol: str,
    model_version: str,
    live_prob: float,
    live_as_of: str,
    generated_at: str,
    limit: int = FORECAST_LOG_LIMIT,
) -> list[dict]:
    """Newest first. Today's row is live and pending; older rows are resolved backtests."""
    probability = round(float(live_prob), 4)
    rows = [
        {
            "id": f"{symbol}-{live_as_of}-v{model_version}",
            "symbol": symbol,
            "made_at": generated_at,
            "as_of_date": live_as_of,
            "target_date": nyse_sessions_after(live_as_of, 5),
            "horizon_days": 5,
            "direction": _direction(probability),
            "prob_up": probability,
            "model_version": model_version,
            "origin": "live",
            "status": "pending",
            "actual_direction": None,
            "actual_return_pct": None,
            "result": None,
        }
    ]
    recent = predictions.copy()
    recent["as_of_date"] = pd.to_datetime(recent["as_of_date"])
    recent = recent.sort_values("as_of_date", ascending=False).head(limit)
    for record in recent.itertuples(index=False):
        as_of = _date(record.as_of_date)
        prob_up = round(float(record.prob_up), 4)
        direction = _direction(prob_up)
        actual_return = float(record.fwd_return_pct)
        actual_direction = "up" if actual_return > 0 else "down"
        rows.append(
            {
                "id": f"{symbol}-{as_of}-v{model_version}",
                "symbol": symbol,
                "made_at": session_close_z(as_of),
                "as_of_date": as_of,
                "target_date": nyse_sessions_after(as_of, 5),
                "horizon_days": 5,
                "direction": direction,
                "prob_up": prob_up,
                "model_version": model_version,
                "origin": "backtest",
                "status": "resolved",
                "actual_direction": actual_direction,
                "actual_return_pct": actual_return,
                "result": "hit" if direction == actual_direction else "miss",
            }
        )
    rows.sort(key=lambda row: row["as_of_date"], reverse=True)
    return rows


def write_artifacts(
    out_dir: Path,
    *,
    symbols: list[str],
    names: dict[str, str],
    prices: dict[str, pd.DataFrame],
    predictions: dict[str, pd.DataFrame],
    live_prob: dict[str, float],
    metrics: dict[str, float | int],
    baselines: list[dict[str, float | str]],
    gate_threshold: float,
    headlines: dict[str, list[dict]],
    sources: dict[str, dict | None],
    window_days: int,
    prices_in_payload: int,
    generated_at: str,
    latency_ms: float,
    sharpe_ratio: float | None = None,
    max_drawdown: float | None = None,
    model_name: str = MODEL_NAME,
    model_version: str = MODEL_VERSION,
    algorithm: str = ALGORITHM,
    mlflow_run_id: str | None = None,
    prior_versions: list[dict] | None = None,
    versions: list[dict] | None = None,
) -> None:
    """Write the four artifact files. Numbers come from the arguments, not from literals."""
    out_dir.mkdir(parents=True, exist_ok=True)
    accuracy = round(float(metrics["directional_accuracy"]), 4)
    gate_passed = accuracy >= float(gate_threshold)
    _write(
        out_dir / "tickers.json",
        {
            "schema_version": "1.0",
            "tickers": [{"symbol": symbol, "name": names[symbol]} for symbol in symbols],
        },
    )
    forecast_rows: list[dict] = []
    oos_frames: list[pd.DataFrame] = []
    kept_dates = _last_session_dates(predictions, FORECAST_LOG_LIMIT)
    for symbol in symbols:
        frame = prices[symbol]
        as_of = _date(frame.sort_values("date")["date"].iloc[-1])
        symbol_predictions = _rows_on_dates(predictions[symbol], kept_dates)
        _write(
            out_dir / "stocks" / f"{symbol}.json",
            build_stock(
                symbol=symbol,
                name=names[symbol],
                prices=frame,
                prices_in_payload=prices_in_payload,
                forecast_prob=live_prob[symbol],
                gate_passed=gate_passed,
                generated_at=generated_at,
                window_days=window_days,
                source=sources.get(symbol),
                headlines=headlines.get(symbol, []),
                model_name=model_name,
                model_version=model_version,
            ),
        )
        forecast_rows.extend(
            build_forecast_rows(
                predictions=symbol_predictions,
                symbol=symbol,
                model_version=model_version,
                live_prob=live_prob[symbol],
                live_as_of=as_of,
                generated_at=generated_at,
                limit=len(symbol_predictions),
            )
        )
        oos_frames.append(predictions[symbol])
    forecast_rows.sort(key=lambda row: row["as_of_date"], reverse=True)
    oos = pd.concat(oos_frames, ignore_index=True)
    oos_dates = pd.to_datetime(oos["as_of_date"])
    resolved = [row for row in forecast_rows if row["status"] == "resolved"]
    hits = sum(row["result"] == "hit" for row in resolved)
    pending = sum(row["status"] == "pending" for row in forecast_rows)
    version = {
        "version": model_version,
        "model_name": model_name,
        "algorithm": algorithm,
        "trained_at": generated_at,
        "directional_accuracy": accuracy,
        "gate_passed": gate_passed,
        "status": "production" if gate_passed else "rejected",
        "mlflow_run_id": mlflow_run_id,
    }
    history = versions if versions is not None else [version, *(prior_versions or [])]
    serving = next((item for item in history if item["status"] == "production"), None)
    production = None
    if serving is not None:
        production = {
            "model_name": serving["model_name"],
            "version": serving["version"],
            "algorithm": serving["algorithm"],
            "trained_at": serving["trained_at"],
        }
    _write(
        out_dir / "model.json",
        {
            "schema_version": "1.0",
            "generated_at": generated_at,
            "is_demo_data": False,
            "production": production,
            "task": {
                "description": TASK_DESCRIPTION,
                "horizon_days": 5,
                "validation": "walk_forward",
                "tickers": list(symbols),
                "test_start": _date(oos_dates.min()),
                "test_end": _date(oos_dates.max()),
                "n_test": int(metrics["n_test"]),
            },
            "metrics": {
                "directional_accuracy": accuracy,
                "precision": _rate(metrics["precision"]),
                "recall": _rate(metrics["recall"]),
                "f1": _rate(metrics["f1"]),
                "sharpe_ratio": None if sharpe_ratio is None else _rate(sharpe_ratio),
                "max_drawdown": None if max_drawdown is None else _rate(max_drawdown),
                "inference_latency_ms": _rate(latency_ms),
                "cost_per_request_usd": None,
            },
            "baselines": [
                {
                    "name": str(row["name"]),
                    "directional_accuracy": _rate(row["directional_accuracy"]),
                }
                for row in baselines
            ],
            "gate": {
                "metric": "directional_accuracy",
                "threshold": float(gate_threshold),
                "passed": gate_passed,
            },
            "weekly_accuracy": build_weekly_accuracy(oos),
            "versions": history,
        },
    )
    _write(
        out_dir / "forecasts.json",
        {
            "schema_version": "1.0",
            "generated_at": generated_at,
            "is_demo_data": False,
            "summary": {
                "resolved": len(resolved),
                "hits": hits,
                "hit_rate": None if not resolved else round(hits / len(resolved), 3),
                "pending": pending,
            },
            "forecasts": forecast_rows,
        },
    )


def _last_session_dates(predictions: dict[str, pd.DataFrame], limit: int) -> set[pd.Timestamp]:
    """The most recent ``limit`` session dates present in any symbol's backtest."""
    frames = [frame for frame in predictions.values() if not frame.empty]
    if not frames:
        return set()
    dates = pd.to_datetime(pd.concat(frames, ignore_index=True)["as_of_date"])
    newest = sorted(dates.drop_duplicates())[-limit:]
    return {pd.Timestamp(value) for value in newest}


def _rows_on_dates(predictions: pd.DataFrame, dates: set[pd.Timestamp]) -> pd.DataFrame:
    if predictions.empty or not dates:
        return predictions.iloc[0:0]
    mask = pd.to_datetime(predictions["as_of_date"]).isin(dates)
    return predictions.loc[mask]


def _rate(value: object) -> float:
    return round(float(value), 4)


def _headlines(headlines: list[dict]) -> list[dict]:
    ordered = sorted(headlines, key=lambda item: item["published_at"], reverse=True)
    kept: list[dict] = []
    seen: set[str] = set()
    for item in ordered:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        kept.append(item)
        if len(kept) == HEADLINE_LIMIT:
            break
    return kept


def _direction(prob_up: float) -> str:
    return "up" if prob_up >= 0.5 else "down"


def _date(value: object) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
