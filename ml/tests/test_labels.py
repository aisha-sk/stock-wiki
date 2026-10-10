"""Contract thresholds. These four boundaries are the whole rule."""

import pytest

from ml.sentiment.labels import label_for


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (19, "neutral"),
        (20, "bullish"),
        (-19, "neutral"),
        (-20, "bearish"),
    ],
)
def test_label_for_boundaries(score: int, expected: str) -> None:
    assert label_for(score) == expected
