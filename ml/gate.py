"""When a candidate is promoted. To change the rule, edit PROMOTION_CHECKS. The threshold is not tuned.

Each check gets the candidate's accuracy, the baselines by name, and the gate threshold,
all rounded to the 4 decimals that are published.
"""

from collections.abc import Callable

Check = Callable[[float, dict[str, float], float], bool]

PROMOTION_CHECKS: dict[str, Check] = {
    "accuracy is at least the gate threshold": lambda accuracy, baselines, threshold: (
        accuracy >= threshold
    ),
    "accuracy beats always_quiet": lambda accuracy, baselines, threshold: (
        "always_quiet" in baselines and accuracy > baselines["always_quiet"]
    ),
}


def failed_checks(
    metrics: dict[str, float | int],
    threshold: float,
    baselines: list[dict[str, float | str]],
) -> list[str]:
    """Names of the promotion checks the candidate fails. Empty means promote."""
    accuracy = round(float(metrics["directional_accuracy"]), 4)
    by_name = {str(row["name"]): round(float(row["directional_accuracy"]), 4) for row in baselines}
    return [
        name
        for name, check in PROMOTION_CHECKS.items()
        if not check(accuracy, by_name, float(threshold))
    ]


def passes_gate(
    metrics: dict[str, float | int],
    threshold: float,
    baselines: list[dict[str, float | str]],
) -> bool:
    return not failed_checks(metrics, threshold, baselines)
