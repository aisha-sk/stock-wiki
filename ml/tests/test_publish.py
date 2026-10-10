"""Publisher tests. Synthetic inputs only, then the real contract validator."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from ml.publish import (
    build_forecast_rows,
    build_stock,
    build_weekly_accuracy,
    nyse_sessions_after,
    write_artifacts,
)

GENERATED_AT = "2026-10-10T17:00:00Z"
ROOT = Path(__file__).resolve().parents[2]


def _prices(n: int = 130) -> pd.DataFrame:
    dates = pd.bdate_range(end="2026-10-09", periods=n)
    close = pd.Series(range(100, 100 + n), dtype=float)
    return pd.DataFrame(
        {
            "date": dates,
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": 1_000.0,
        }
    )


def _predictions() -> pd.DataFrame:
    # Ten resolved sessions. The last one is a miss so hit_rate is not trivial.
    rows = []
    start = pd.Timestamp("2026-06-01")
    for offset in range(10):
        day = start + pd.Timedelta(days=offset * 7)
        up = offset != 9
        rows.append(
            {
                "symbol": "TSLA",
                "as_of_date": day,
                "prob_up": 0.8,
                "y_true": 1 if up else 0,
                "fwd_return_pct": 1.5 if up else -2.0,
            }
        )
    return pd.DataFrame(rows)


def _headlines() -> list[dict]:
    return [
        {
            "id": "bbbbbbbbbbbb",
            "source": "news",
            "publisher": "Example Wire",
            "title": "Older headline",
            "url": "https://example.com/older",
            "published_at": "2026-10-08T12:00:00Z",
            "score": -30,
            "label": "bearish",
        },
        {
            "id": "aaaaaaaaaaaa",
            "source": "news",
            "publisher": "Example Wire",
            "title": "Newer headline",
            "url": "https://example.com/newer",
            "published_at": "2026-10-09T12:00:00Z",
            "score": 25,
            "label": "bullish",
        },
    ]


def _source() -> dict:
    return {
        "source": "news",
        "display_name": "News media",
        "score": 8,
        "label": "neutral",
        "doc_count": 2,
        "note": "2 articles, last 7 days",
        "method": "finbert",
        "previous_score": None,
    }


def test_nyse_target_is_five_sessions_after_the_friday() -> None:
    assert nyse_sessions_after("2026-10-09", 5) == "2026-10-16"


def test_weekly_accuracy_uses_mondays_and_keeps_the_last_12() -> None:
    frame = _predictions()
    extra = []
    for offset in range(20):
        day = pd.Timestamp("2025-01-06") + pd.Timedelta(days=offset * 7)
        extra.append(
            {
                "symbol": "TSLA",
                "as_of_date": day,
                "prob_up": 0.8,
                "y_true": 1,
                "fwd_return_pct": 1.0,
            }
        )
    weeks = build_weekly_accuracy(pd.concat([pd.DataFrame(extra), frame], ignore_index=True))

    assert len(weeks) == 12
    assert weeks == sorted(weeks, key=lambda week: week["week_start"])
    assert all(pd.Timestamp(week["week_start"]).dayofweek == 0 for week in weeks)


def test_failed_gate_nulls_the_forecast_and_keeps_a_live_log_row() -> None:
    stock = build_stock(
        symbol="TSLA",
        name="Tesla, Inc.",
        prices=_prices(),
        prices_in_payload=120,
        forecast_prob=0.4,
        gate_passed=False,
        generated_at=GENERATED_AT,
        window_days=7,
        source=_source(),
        headlines=_headlines(),
    )
    rows = build_forecast_rows(
        predictions=_predictions(),
        symbol="TSLA",
        model_version="1",
        live_prob=0.4,
        live_as_of="2026-10-09",
        generated_at=GENERATED_AT,
        limit=60,
    )

    assert stock["is_demo_data"] is False
    assert stock["forecast"] is None
    assert stock["sentiment"]["gap"] is None
    assert [item["source"] for item in stock["sentiment"]["sources"]] == ["news"]
    assert len(stock["prices"]) == 120
    assert stock["prices"][-1]["date"] == stock["quote"]["as_of"]
    assert stock["quote"]["price"] == stock["prices"][-1]["close"]
    assert stock["headlines"][0]["published_at"] > stock["headlines"][1]["published_at"]
    assert rows[0]["origin"] == "live"
    assert rows[0]["status"] == "pending"
    assert rows[0]["actual_direction"] is None
    assert rows[1]["origin"] == "backtest"
    assert rows[1]["status"] == "resolved"
    assert rows[0]["id"] == "TSLA-2026-10-09-v1"


def test_written_artifacts_match_the_contract(tmp_path: Path) -> None:
    write_artifacts(
        tmp_path,
        symbols=["TSLA"],
        names={"TSLA": "Tesla, Inc."},
        prices={"TSLA": _prices()},
        predictions={"TSLA": _predictions()},
        live_prob={"TSLA": 0.4},
        metrics={
            "directional_accuracy": 0.46,
            "precision": 0.41,
            "recall": 0.24,
            "f1": 0.30,
            "n_test": 10,
        },
        baselines=[
            {"name": "always_up", "directional_accuracy": 0.5},
            {"name": "previous_direction", "directional_accuracy": 0.48},
        ],
        gate_threshold=0.52,
        headlines={"TSLA": _headlines()},
        sources={"TSLA": _source()},
        window_days=7,
        prices_in_payload=120,
        generated_at=GENERATED_AT,
        latency_ms=1.5,
    )

    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_contracts.py"), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    model = json.loads((tmp_path / "model.json").read_text(encoding="utf-8"))
    assert model["production"] is None
    assert model["versions"][0]["status"] == "rejected"
    assert model["versions"][0]["model_name"] == "direction-lr"
    assert model["gate"]["passed"] is False
    assert model["gate"]["threshold"] == 0.52
    forecasts = json.loads((tmp_path / "forecasts.json").read_text(encoding="utf-8"))
    assert forecasts["summary"]["pending"] == 1
    assert forecasts["summary"]["resolved"] == 10
    assert forecasts["summary"]["hit_rate"] == 0.9
