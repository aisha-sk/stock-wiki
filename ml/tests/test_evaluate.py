"""Metric definitions. Positive class is up."""

import numpy as np
import pandas as pd
import pytest

from ml.evaluate import baseline_scores, classification_metrics, strategy_backtest


def test_classification_metrics_treat_up_as_the_positive_class() -> None:
    # Predictions at 0.5 and above are up: 1, 1, 0, 1 against labels 1, 0, 1, 1.
    metrics = classification_metrics([1, 0, 1, 1], [0.6, 0.7, 0.4, 0.8])

    assert metrics["directional_accuracy"] == pytest.approx(0.5)
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)
    assert metrics["f1"] == pytest.approx(2 / 3)


def test_baselines_use_the_same_rows() -> None:
    # Trailing return of 0 is not up, so previous_direction predicts down there.
    baselines = baseline_scores([1, 0, 1], [0.1, -0.2, 0.0])
    by_name = {row["name"]: row["directional_accuracy"] for row in baselines}

    assert by_name["always_up"] == pytest.approx(2 / 3)
    assert by_name["previous_direction"] == pytest.approx(2 / 3)


def test_strategy_backtest_uses_every_fifth_session() -> None:
    rows = []
    for offset in range(10):
        rows.append(
            {
                "as_of_date": pd.Timestamp("2026-01-01") + pd.Timedelta(days=offset),
                "prob_up": 0.8,
                "fwd_return_pct": 10.0 if offset == 0 else -50.0,
            }
        )
    result = strategy_backtest(pd.DataFrame(rows))
    periods = np.array([0.10, -0.50])
    sharpe = float(periods.mean() / periods.std(ddof=1) * np.sqrt(252 / 5))

    assert result["sharpe_ratio"] == pytest.approx(sharpe)
    assert result["max_drawdown"] == pytest.approx(-0.5)
