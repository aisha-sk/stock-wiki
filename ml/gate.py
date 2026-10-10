"""The fixed directional-accuracy gate. The threshold is not tuned."""


def passes_gate(metrics: dict[str, float | int], threshold: float) -> bool:
    """True when directional accuracy is at least the threshold, including equality."""
    return float(metrics["directional_accuracy"]) >= float(threshold)
