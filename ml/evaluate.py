"""Out-of-sample scores. The positive class is ``up`` (``y == 1``)."""

import numpy as np


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
