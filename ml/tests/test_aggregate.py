"""Offline rollup of headline scores into one news source."""

import json
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator, FormatChecker

from ml.sentiment.aggregate import aggregate_news

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "schemas" / "stock.schema.json"
)
NOW = pd.Timestamp("2026-10-10T12:00:00Z")


def _doc(score: int, published_at: str) -> dict:
    return {"score": score, "published_at": published_at}


def test_aggregate_means_the_last_7_days_and_the_window_before() -> None:
    documents = [
        _doc(40, "2026-10-09T12:00:00Z"),
        _doc(20, "2026-10-08T12:00:00Z"),
        _doc(-40, "2026-10-01T12:00:00Z"),
        _doc(100, "2026-09-01T12:00:00Z"),
    ]

    summary = aggregate_news(documents, now=NOW, window_days=7)

    assert summary is not None
    assert summary["source"] == "news"
    assert summary["display_name"] == "News media"
    assert summary["method"] == "finbert"
    assert summary["score"] == 30
    assert summary["label"] == "bullish"
    assert summary["doc_count"] == 2
    assert summary["note"] == "2 articles, last 7 days"
    assert summary["previous_score"] == -40


def test_previous_score_is_none_when_the_prior_window_is_empty() -> None:
    documents = [_doc(10, "2026-10-09T12:00:00Z")]

    summary = aggregate_news(documents, now=NOW, window_days=7)

    assert summary is not None
    assert summary["previous_score"] is None
    assert summary["note"] == "1 article, last 7 days"


def test_no_recent_documents_leaves_the_source_out() -> None:
    documents = [_doc(-40, "2026-10-01T12:00:00Z")]

    assert aggregate_news(documents, now=NOW, window_days=7) is None


def test_aggregate_matches_the_source_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    item = dict(schema["properties"]["sentiment"]["properties"]["sources"]["items"])
    item["$defs"] = schema["$defs"]
    summary = aggregate_news([_doc(8, "2026-10-09T12:00:00Z")], now=NOW, window_days=7)

    Draft202012Validator(item, format_checker=FormatChecker()).validate(summary)
