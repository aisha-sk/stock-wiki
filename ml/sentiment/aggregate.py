"""Roll a list of scored documents up into the news source object."""

import pandas as pd

from ml.sentiment.labels import label_for


def aggregate_news(
    documents: list[dict],
    *,
    now: pd.Timestamp,
    window_days: int = 7,
) -> dict | None:
    """Mean score over the last ``window_days``, plus the window before that."""
    return aggregate_posts(
        documents,
        source="news",
        display_name="News media",
        now=now,
        window_days=window_days,
        noun="article",
    )


def aggregate_posts(
    documents: list[dict],
    *,
    source: str,
    display_name: str,
    now: pd.Timestamp,
    window_days: int = 7,
    noun: str = "article",
    note: str | None = None,
) -> dict | None:
    """Mean score for one text source. ``None`` when the current window is empty."""
    now_utc = _as_utc(now)
    current_start = now_utc - pd.Timedelta(days=window_days)
    previous_start = now_utc - pd.Timedelta(days=window_days * 2)
    current: list[dict] = []
    previous: list[int] = []
    for document in documents:
        published = _as_utc(document["published_at"])
        score = int(document["score"])
        if current_start <= published <= now_utc:
            current.append(document)
        elif previous_start <= published < current_start:
            previous.append(score)
    if not current:
        return None
    source_score = _rounded_mean([int(document["score"]) for document in current])
    word = noun if len(current) == 1 else f"{noun}s"
    caption = note or f"{len(current)} {word}, last {window_days} days"
    return {
        "source": source,
        "display_name": display_name,
        "score": source_score,
        "label": label_for(source_score),
        "doc_count": len(current),
        "note": caption,
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
