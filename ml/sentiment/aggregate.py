"""Roll a list of scored documents up into the news source object."""

import pandas as pd

from ml.sentiment.labels import label_for


def aggregate_news(
    documents: list[dict],
    *,
    now: pd.Timestamp,
    window_days: int = 7,
) -> dict | None:
    """Mean score over the last ``window_days``, plus the window before that.

    Returns ``None`` when the current window has no documents. The publisher
    leaves that source out of the array rather than writing a zero.
    """
    now_utc = _as_utc(now)
    current_start = now_utc - pd.Timedelta(days=window_days)
    previous_start = now_utc - pd.Timedelta(days=window_days * 2)
    current: list[int] = []
    previous: list[int] = []
    for document in documents:
        published = _as_utc(document["published_at"])
        score = int(document["score"])
        if current_start <= published <= now_utc:
            current.append(score)
        elif previous_start <= published < current_start:
            previous.append(score)
    if not current:
        return None
    source_score = _rounded_mean(current)
    noun = "article" if len(current) == 1 else "articles"
    return {
        "source": "news",
        "display_name": "News media",
        "score": source_score,
        "label": label_for(source_score),
        "doc_count": len(current),
        "note": f"{len(current)} {noun}, last {window_days} days",
        "method": "finbert",
        "previous_score": None if not previous else _rounded_mean(previous),
    }


def _rounded_mean(scores: list[int]) -> int:
    return round(sum(scores) / len(scores))


def _as_utc(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")
