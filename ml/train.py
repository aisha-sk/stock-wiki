"""Expanding-window walk-forward models.

Folds are split by session date, so pooling tickers cannot leak one ticker's
future into another's training rows. The scaler, when the algorithm uses one,
is fit inside each training fold only. Reported metrics use the out-of-sample
predictions, never an in-sample score from the final fit.
"""

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from ml.config import load_config
from ml.evaluate import baseline_scores, classification_metrics
from ml.features import (
    FEATURE_COLUMNS,
    NEWS_LAG_COLUMN,
    add_features,
    add_target,
    typical_move_pct,
)
from ml.ingest.prices import load_prices

INITIAL_SESSIONS = 252
TEST_BLOCK = 21
STEP = 21
PURGE = 5
ALGORITHMS = ("xgboost",)
XGB_PARAMS = {
    "n_estimators": 200,
    "max_depth": 3,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "random_state": 0,
    "n_jobs": 1,
}


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
    model: XGBClassifier
    latest_features: pd.DataFrame


@dataclass(frozen=True)
class PooledTrainResult:
    predictions: pd.DataFrame
    metrics: dict[str, float | int]
    baselines: list[dict[str, float | str]]
    forecasts: dict[str, dict[str, object]]
    folds: tuple[Fold, ...]
    model: XGBClassifier
    latest_features: dict[str, pd.DataFrame]
    algorithm: str


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
    algorithm: str = "xgboost",
) -> TrainResult:
    """Collect purged walk-forward predictions, then forecast the latest session."""
    pooled = walk_forward_pooled(
        {symbol: prices},
        horizon=horizon,
        initial=initial,
        block=block,
        step=step,
        purge=purge,
        news_documents=None if not news_documents else {symbol: news_documents},
        algorithm=algorithm,
    )
    return TrainResult(
        predictions=pooled.predictions,
        metrics=pooled.metrics,
        baselines=pooled.baselines,
        forecast=pooled.forecasts[symbol],
        folds=pooled.folds,
        model=pooled.model,
        latest_features=pooled.latest_features[symbol],
    )


def walk_forward_pooled(
    prices_by_symbol: dict[str, pd.DataFrame],
    *,
    horizon: int = 5,
    initial: int = INITIAL_SESSIONS,
    block: int = TEST_BLOCK,
    step: int = STEP,
    purge: int = PURGE,
    news_documents: dict[str, list[dict]] | None = None,
    algorithm: str = "xgboost",
) -> PooledTrainResult:
    """One model for every symbol. Each fold's train and test sets are dates, not rows."""
    if algorithm not in ALGORITHMS:
        raise ValueError(f"unknown algorithm {algorithm}")
    documents = news_documents or {}
    use_news = any(documents.get(symbol) for symbol in prices_by_symbol)
    columns = list(FEATURE_COLUMNS)
    if use_news:
        columns.append(NEWS_LAG_COLUMN)

    prepared: list[pd.DataFrame] = []
    latest_rows: dict[str, pd.Series] = {}
    for symbol, prices in prices_by_symbol.items():
        ordered = prices.sort_values("date").reset_index(drop=True)
        featured = add_target(
            add_features(ordered, news_documents=documents.get(symbol) if use_news else None),
            horizon=horizon,
        )
        featured["symbol"] = symbol
        feature_ready = featured.dropna(subset=columns)
        if feature_ready.empty:
            raise RuntimeError(f"{symbol} has no sessions with complete features")
        forecast_row = feature_ready.iloc[-1]
        if pd.Timestamp(forecast_row["date"]) != pd.Timestamp(ordered["date"].iloc[-1]):
            raise RuntimeError(f"{symbol} latest session is missing features")
        latest_rows[symbol] = forecast_row
        prepared.append(featured)

    labelled = pd.concat(prepared, ignore_index=True)
    model_rows = labelled.dropna(subset=[*columns, "fwd_return_pct"]).reset_index(drop=True)
    dates = [pd.Timestamp(value) for value in pd.to_datetime(model_rows["date"]).drop_duplicates().sort_values()]
    blocks: list[pd.DataFrame] = []
    folds: list[Fold] = []
    for train_slice, test_slice in _iter_folds(
        len(dates), initial=initial, block=block, step=step, purge=purge
    ):
        train_dates = dates[train_slice]
        test_dates = dates[test_slice]
        train = model_rows[pd.to_datetime(model_rows["date"]).isin(train_dates)]
        test = model_rows[pd.to_datetime(model_rows["date"]).isin(test_dates)]
        threshold = typical_move_pct(train["fwd_return_pct"])
        train_y = _large_labels(train["fwd_return_pct"], threshold)
        test_y = _large_labels(test["fwd_return_pct"], threshold)
        previous = _large_labels(test["ret_5d"] * 100.0, threshold)
        model = _new_model(algorithm)
        model.fit(train[columns], train_y)
        probabilities = _positive_probability(model, test[columns])
        blocks.append(
            pd.DataFrame(
                {
                    "symbol": test["symbol"].to_numpy(),
                    "as_of_date": pd.to_datetime(test["date"]).to_numpy(),
                    "prob_large": probabilities,
                    "y_true": test_y,
                    "fwd_return_pct": test["fwd_return_pct"].to_numpy(dtype=float),
                    "typical_move_pct": threshold,
                    "previous_was_large": previous,
                }
            )
        )
        folds.append(Fold(train_dates=tuple(train_dates), test_dates=tuple(test_dates)))
    if not blocks:
        raise RuntimeError(
            f"{len(model_rows)} labelled sessions is not enough for a {initial}-session walk-forward window"
        )

    predictions = pd.concat(blocks, ignore_index=True)
    metrics = classification_metrics(predictions["y_true"], predictions["prob_large"])
    metrics["n_test"] = len(predictions)
    baselines = baseline_scores(predictions["y_true"], predictions["previous_was_large"])
    predictions = predictions.drop(columns=["previous_was_large"])

    live_threshold = typical_move_pct(model_rows["fwd_return_pct"])
    final = _new_model(algorithm)
    final.fit(model_rows[columns], _large_labels(model_rows["fwd_return_pct"], live_threshold))
    forecasts: dict[str, dict[str, object]] = {}
    latest_features: dict[str, pd.DataFrame] = {}
    for symbol, forecast_row in latest_rows.items():
        latest = pd.DataFrame([forecast_row[columns]])
        prob_large = float(_positive_probability(final, latest)[0])
        latest_features[symbol] = latest
        forecasts[symbol] = {
            "symbol": symbol,
            "as_of_date": pd.Timestamp(forecast_row["date"]),
            "horizon_days": horizon,
            "move": "large" if prob_large >= 0.5 else "quiet",
            "prob_large": prob_large,
            "typical_move_pct": live_threshold,
            "confidence": float(max(prob_large, 1.0 - prob_large)),
        }
    return PooledTrainResult(
        predictions=predictions,
        metrics=metrics,
        baselines=baselines,
        forecasts=forecasts,
        folds=tuple(folds),
        model=final,
        latest_features=latest_features,
        algorithm=algorithm,
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
    parser = argparse.ArgumentParser(description="Walk-forward XGBoost large-move model.")
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


def _new_model(algorithm: str) -> XGBClassifier:
    if algorithm != "xgboost":
        raise ValueError(f"unknown algorithm {algorithm}")
    return XGBClassifier(**XGB_PARAMS)


def _large_labels(returns_pct: object, threshold_pct: float) -> np.ndarray:
    return (np.abs(np.asarray(returns_pct, dtype=float)) > threshold_pct).astype(int)


def _positive_probability(model: XGBClassifier, features: pd.DataFrame) -> np.ndarray:
    probabilities = model.predict_proba(features)
    classes = [int(label) for label in model.classes_]
    if 1 not in classes:
        return np.zeros(len(features), dtype=float)
    return probabilities[:, classes.index(1)]


if __name__ == "__main__":
    raise SystemExit(main())
