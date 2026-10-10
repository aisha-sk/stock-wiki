"""Expanding-window walk-forward logistic regression.

The scaler is fit inside each training fold only. Reported metrics use the
out-of-sample predictions, never an in-sample score from the final fit.
"""

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.config import load_config
from ml.evaluate import baseline_scores, classification_metrics
from ml.features import FEATURE_COLUMNS, NEWS_LAG_COLUMN, add_features, add_target
from ml.ingest.prices import load_prices

INITIAL_SESSIONS = 252
TEST_BLOCK = 21
STEP = 21
PURGE = 5


@dataclass(frozen=True)
class Fold:
    train_dates: tuple[pd.Timestamp, ...]
    test_dates: tuple[pd.Timestamp, ...]


@dataclass(frozen=True)
class TrainResult:
    predictions: pd.DataFrame
    metrics: dict[str, float | int]
    baselines: list[dict[str, float | str]]
    forecast: dict[str, object]
    folds: tuple[Fold, ...]
    model: Pipeline
    latest_features: pd.DataFrame


def walk_forward(
    prices: pd.DataFrame,
    *,
    symbol: str,
    horizon: int = 5,
    initial: int = INITIAL_SESSIONS,
    block: int = TEST_BLOCK,
    step: int = STEP,
    purge: int = PURGE,
    news_documents: list[dict] | None = None,
) -> TrainResult:
    """Collect purged walk-forward predictions, then forecast the latest session."""
    ordered = prices.sort_values("date").reset_index(drop=True)
    featured = add_target(
        add_features(ordered, news_documents=news_documents),
        horizon=horizon,
    )
    columns = list(FEATURE_COLUMNS)
    if news_documents:
        columns.append(NEWS_LAG_COLUMN)
    model_rows = featured.dropna(subset=[*columns, "y"]).reset_index(drop=True)
    feature_ready = featured.dropna(subset=columns)
    if feature_ready.empty:
        raise RuntimeError(f"{symbol} has no sessions with complete features")
    forecast_row = feature_ready.iloc[-1]
    if pd.Timestamp(forecast_row["date"]) != pd.Timestamp(ordered["date"].iloc[-1]):
        raise RuntimeError(f"{symbol} latest session is missing features")

    blocks: list[pd.DataFrame] = []
    folds: list[Fold] = []
    for train_slice, test_slice in _iter_folds(
        len(model_rows), initial=initial, block=block, step=step, purge=purge
    ):
        train = model_rows.iloc[train_slice]
        test = model_rows.iloc[test_slice]
        pipeline = _new_pipeline()
        pipeline.fit(train[columns], train["y"].astype(int))
        probabilities = _prob_up(pipeline, test[columns])
        blocks.append(
            pd.DataFrame(
                {
                    "symbol": symbol,
                    "as_of_date": pd.to_datetime(test["date"]).to_numpy(),
                    "prob_up": probabilities,
                    "y_true": test["y"].astype(int).to_numpy(),
                    "fwd_return_pct": test["fwd_return_pct"].to_numpy(dtype=float),
                    "ret_5d": test["ret_5d"].to_numpy(dtype=float),
                }
            )
        )
        folds.append(
            Fold(
                train_dates=tuple(pd.Timestamp(value) for value in train["date"]),
                test_dates=tuple(pd.Timestamp(value) for value in test["date"]),
            )
        )
    if not blocks:
        raise RuntimeError(
            f"{symbol} has {len(model_rows)} labelled sessions, which is not enough "
            f"for a {initial}-session walk-forward window"
        )

    predictions = pd.concat(blocks, ignore_index=True)
    metrics = classification_metrics(predictions["y_true"], predictions["prob_up"])
    metrics["n_test"] = len(predictions)
    baselines = baseline_scores(predictions["y_true"], predictions["ret_5d"])
    predictions = predictions.drop(columns=["ret_5d"])

    final = _new_pipeline()
    final.fit(model_rows[columns], model_rows["y"].astype(int))
    latest = pd.DataFrame([forecast_row[columns]])
    prob_up = float(_prob_up(final, latest)[0])
    forecast = {
        "symbol": symbol,
        "as_of_date": pd.Timestamp(forecast_row["date"]),
        "horizon_days": horizon,
        "direction": "up" if prob_up >= 0.5 else "down",
        "prob_up": prob_up,
        "confidence": float(max(prob_up, 1.0 - prob_up)),
    }
    return TrainResult(
        predictions=predictions,
        metrics=metrics,
        baselines=baselines,
        forecast=forecast,
        folds=tuple(folds),
        model=final,
        latest_features=latest,
    )


def format_report(
    symbol: str,
    metrics: dict[str, float | int],
    baselines: list[dict[str, float | str]],
) -> str:
    lines = [f"{symbol}  n_test={metrics['n_test']}"]
    lines.append(
        f"{'model':<22} directional_accuracy={float(metrics['directional_accuracy']):.3f}  "
        f"precision={float(metrics['precision']):.3f}  "
        f"recall={float(metrics['recall']):.3f}  "
        f"f1={float(metrics['f1']):.3f}"
    )
    for baseline in baselines:
        lines.append(
            f"{baseline['name']!s:<22} "
            f"directional_accuracy={float(baseline['directional_accuracy']):.3f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Walk-forward logistic regression.")
    parser.add_argument("--tickers", nargs="+", required=True)
    args = parser.parse_args(argv)
    horizon = load_config().horizon_days
    for symbol in args.tickers:
        prices = load_prices(symbol)
        result = walk_forward(prices, symbol=symbol.upper(), horizon=horizon)
        print(format_report(symbol.upper(), result.metrics, result.baselines))
    return 0


def _iter_folds(
    n_rows: int,
    *,
    initial: int,
    block: int,
    step: int,
    purge: int,
):
    """Expanding train window, then a test block. The last ``purge`` train rows are dropped."""
    test_start = initial
    while test_start < n_rows:
        train_stop = test_start - purge
        test_stop = min(n_rows, test_start + block)
        if train_stop <= 0 or test_start >= test_stop:
            break
        yield slice(0, train_stop), slice(test_start, test_stop)
        if test_stop == n_rows:
            break
        test_start += step


def _new_pipeline() -> Pipeline:
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(max_iter=1000, solver="lbfgs", random_state=0),
            ),
        ]
    )


def _prob_up(pipeline: Pipeline, features: pd.DataFrame) -> np.ndarray:
    model = pipeline.named_steps["model"]
    probabilities = pipeline.predict_proba(features)
    classes = [int(label) for label in model.classes_]
    if 1 not in classes:
        return np.zeros(len(features), dtype=float)
    return probabilities[:, classes.index(1)]


if __name__ == "__main__":
    raise SystemExit(main())
