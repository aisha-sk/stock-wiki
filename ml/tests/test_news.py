"""Offline news normalisation. No network."""

import hashlib
import json
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator, FormatChecker

from ml.ingest.news import (
    dedupe_headlines,
    fetch_headlines,
    from_finnhub_item,
    from_rss_entry,
    from_yfinance_item,
    headline_id,
    normalize_headline,
)
from ml.sentiment.run import apply_scores

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "schemas" / "stock.schema.json"
)


def _headline_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    item = dict(schema["properties"]["headlines"]["items"])
    item["$defs"] = schema["$defs"]
    return Draft202012Validator(item, format_checker=FormatChecker())


def test_headline_id_is_first_12_hex_chars_of_sha1_url() -> None:
    url = "https://example.com/tsla/story"
    assert headline_id(url) == hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def test_normalize_drops_empty_titles_and_formats_utc() -> None:
    kept = normalize_headline(
        title="  Tesla expands a plant  ",
        url="https://example.com/tsla/story",
        publisher="Reuters",
        published_at="2026-10-09T11:45:00-04:00",
    )
    dropped = normalize_headline(
        title="   ",
        url="https://example.com/empty",
        publisher="Reuters",
        published_at="2026-10-09T11:45:00Z",
    )

    assert dropped is None
    assert kept is not None
    assert kept["title"] == "Tesla expands a plant"
    assert kept["source"] == "news"
    assert kept["publisher"] == "Reuters"
    assert kept["published_at"] == "2026-10-09T15:45:00Z"
    assert kept["id"] == headline_id(kept["url"])


def test_dedupe_keeps_the_newest_copy_of_an_id() -> None:
    url = "https://example.com/tsla/story"
    older = normalize_headline(
        title="Older copy",
        url=url,
        publisher="Reuters",
        published_at="2026-10-08T12:00:00Z",
    )
    newer = normalize_headline(
        title="Newer copy",
        url=url,
        publisher="Reuters",
        published_at="2026-10-09T12:00:00Z",
    )
    assert older is not None and newer is not None

    kept = dedupe_headlines([older, newer])

    assert len(kept) == 1
    assert kept[0]["title"] == "Newer copy"


def test_parsers_share_one_document_shape() -> None:
    finnhub = from_finnhub_item(
        {
            "headline": "Tesla deliveries rise",
            "url": "https://example.com/finnhub",
            "source": "Reuters",
            "datetime": 1760000000,
        }
    )
    yahoo = from_yfinance_item(
        {
            "content": {
                "title": "Tesla deliveries rise",
                "pubDate": "2026-10-09T11:45:00Z",
                "provider": {"displayName": "Bloomberg"},
                "canonicalUrl": {"url": "https://example.com/yahoo"},
            }
        }
    )
    rss = from_rss_entry(
        {
            "title": "Tesla deliveries rise",
            "link": "https://example.com/rss",
            "published": "2026-10-09T11:45:00Z",
            "source": {"title": "CNBC"},
        }
    )

    for document in (finnhub, yahoo, rss):
        assert document is not None
        assert set(document) == {"id", "source", "publisher", "title", "url", "published_at"}
        assert document["source"] == "news"
        assert document["published_at"].endswith("Z")


def test_fetch_prefers_finnhub_then_yahoo_then_rss() -> None:
    finnhub_doc = normalize_headline(
        title="From Finnhub",
        url="https://example.com/finnhub",
        publisher="Reuters",
        published_at="2026-10-09T12:00:00Z",
    )
    yahoo_doc = normalize_headline(
        title="From Yahoo",
        url="https://example.com/yahoo",
        publisher="Bloomberg",
        published_at="2026-10-09T12:00:00Z",
    )
    rss_doc = normalize_headline(
        title="From RSS",
        url="https://example.com/rss",
        publisher="CNBC",
        published_at="2026-10-09T12:00:00Z",
    )
    assert finnhub_doc and yahoo_doc and rss_doc

    def finnhub(_symbol: str, _api_key: str, _now: pd.Timestamp) -> list[dict]:
        return [finnhub_doc]

    def yahoo(_symbol: str) -> list[dict]:
        return [yahoo_doc]

    def rss(_symbol: str) -> list[dict]:
        return [rss_doc]

    now = pd.Timestamp("2026-10-10T12:00:00Z")
    with_key = fetch_headlines(
        "TSLA",
        now=now,
        api_key="test-key",
        finnhub=finnhub,
        yahoo=yahoo,
        rss=rss,
    )
    without_key = fetch_headlines(
        "TSLA",
        now=now,
        api_key="",
        finnhub=finnhub,
        yahoo=yahoo,
        rss=rss,
    )
    yahoo_empty = fetch_headlines(
        "TSLA",
        now=now,
        api_key="",
        finnhub=finnhub,
        yahoo=lambda _symbol: [],
        rss=rss,
    )

    assert [item["title"] for item in with_key] == ["From Finnhub"]
    assert [item["title"] for item in without_key] == ["From Yahoo"]
    assert [item["title"] for item in yahoo_empty] == ["From RSS"]


def test_scored_headline_matches_the_contract_schema() -> None:
    document = normalize_headline(
        title="Regulators open a review into driver-assist claims",
        url="https://example.com/tsla/3f2a9c1b7e10",
        publisher="Example Wire",
        published_at="2026-10-09T11:45:00Z",
    )
    assert document is not None
    scored = apply_scores([document], [-48])[0]

    _headline_validator().validate(scored)
