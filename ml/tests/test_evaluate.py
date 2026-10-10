"""Metric definitions. Positive class is up."""

import pytest

from ml.evaluate import baseline_scores, classification_metrics


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
