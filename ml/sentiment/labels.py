"""Sentiment labels. The contract thresholds live only in this function."""


def label_for(score: int) -> str:
    """Map an integer score to bullish, bearish, or neutral."""
    if score >= 20:
        return "bullish"
    if score <= -20:
        return "bearish"
    return "neutral"
