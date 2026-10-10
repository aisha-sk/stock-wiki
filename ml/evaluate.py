"""Out-of-sample scores. The positive class is ``up`` (``y == 1``)."""

import math

import numpy as np
import pandas as pd


def classification_metrics(y_true: object, prob_up: object) -> dict[str, float]:
    """Accuracy, precision, recall and F1. A probability of 0.5 or more is ``up``."""
    y = np.asarray(y_true, dtype=int)
    probability = np.asarray(prob_up, dtype=float)
    predicted = (probability >= 0.5).astype(int)
    true_positive = int(np.sum((predicted == 1) & (y == 1)))
    false_positive = int(np.sum((predicted == 1) & (y == 0)))
    false_negative = int(np.sum((predicted == 0) & (y == 1)))
    return {
        "directional_accuracy": float(np.mean(predicted == y)),
        "precision": _ratio(true_positive, true_positive + false_positive),
        "recall": _ratio(true_positive, true_positive + false_negative),
        "f1": _f1(true_positive, false_positive, false_negative),
    }


def baseline_scores(y_true: object, trailing_return_5d: object) -> list[dict[str, float | str]]:
    """Score ``always_up`` and ``previous_direction`` on the same rows as the model.

    ``previous_direction`` predicts up only when the trailing 5-day return is positive.
    """
    y = np.asarray(y_true, dtype=int)
    trailing = np.asarray(trailing_return_5d, dtype=float)
    previous = (trailing > 0).astype(int)
    return [
        {"name": "always_up", "directional_accuracy": float(np.mean(y == 1))},
        {
            "name": "previous_direction",
            "directional_accuracy": float(np.mean(previous == y)),
        },
    ]


def strategy_backtest(predictions: pd.DataFrame) -> dict[str, float | None]:
    """Long when the model says up, flat otherwise, on non-overlapping 5-day periods.

    ``sharpe_ratio`` is ``mean / std * sqrt(252 / 5)`` of those period returns.
    ``max_drawdown`` is the equity curve's worst drop, as a negative fraction.
    """
    frame = predictions.copy()
    frame["as_of_date"] = pd.to_datetime(frame["as_of_date"])
    dates = sorted(frame["as_of_date"].unique())
    chosen = set(dates[::5])
    held = frame["as_of_date"].isin(chosen)
    period_return = np.where(
        frame.loc[held, "prob_up"].to_numpy() >= 0.5,
        frame.loc[held, "fwd_return_pct"].to_numpy(dtype=float) / 100.0,
        0.0,
    )
    sampled = frame.loc[held, ["as_of_date"]].copy()
    sampled["strategy_return"] = period_return
    periods = sampled.groupby("as_of_date", sort=True)["strategy_return"].mean()
    if periods.empty:
        return {"sharpe_ratio": None, "max_drawdown": None}
    equity = np.concatenate([[1.0], np.cumprod(1.0 + periods.to_numpy(dtype=float))])
    peak = np.maximum.accumulate(equity)
    drawdown = float(np.min(equity / peak - 1.0))
    deviation = float(periods.std(ddof=1)) if len(periods) > 1 else 0.0
    sharpe = None
    if deviation > 0:
        sharpe = float(periods.mean() / deviation * math.sqrt(252 / 5))
    return {"sharpe_ratio": sharpe, "max_drawdown": min(0.0, drawdown)}


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator / denominator)


def _f1(true_positive: int, false_positive: int, false_negative: int) -> float:
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    if precision + recall == 0:
        return 0.0
    return float(2 * precision * recall / (precision + recall))
