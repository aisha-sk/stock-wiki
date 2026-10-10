"""FinBERT sign check. Marked slow because it loads model weights."""

import pytest

from ml.sentiment.finbert import score_from_probabilities, score_titles


def test_score_uses_positive_probability_minus_negative() -> None:
    score = score_from_probabilities(
        [
            {"label": "positive", "score": 0.7},
            {"label": "negative", "score": 0.2},
            {"label": "neutral", "score": 0.1},
        ]
    )

    assert score == 50


@pytest.mark.slow
def test_finbert_scores_clear_headlines_with_the_right_sign() -> None:
    positive, negative = score_titles(
        [
            "The company reported record earnings and raised its dividend",
            "The company filed for bankruptcy amid a massive fraud investigation",
        ]
    )

    assert positive > 0
    assert negative < 0
