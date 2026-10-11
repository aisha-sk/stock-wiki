"""Headline ingestion. Finnhub, then Yahoo Finance, then Google News RSS."""

import hashlib
import json
import os
import re
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pandas as pd

LOOKBACK_DAYS = 14
_DOCUMENT_KEYS = ("id", "source", "publisher", "title", "url", "published_at")
_JUNK_TITLE = re.compile(
    r"stock price, news, quote and history"
    r"|\b[A-Z]{1,6}\d{6}[CP]\d{8}\b"
    r"|\b\d+(?:\.\d+)?\s+(?:put|call)\b"
    r"|\boptions?\s+chain\b",
    re.IGNORECASE,
)

FinnhubFetcher = Callable[[str, str, pd.Timestamp], list[dict]]
HeadlineFetcher = Callable[[str], list[dict]]


def is_junk_headline(title: str) -> bool:
    """Quote pages and option-chain listings are not articles."""
    return _JUNK_TITLE.search(str(title)) is not None


def without_junk(documents: list[dict]) -> list[dict]:
    """Drop market-data pages before they are scored or published."""
    return [document for document in documents if not is_junk_headline(str(document.get("title") or ""))]


def headline_id(url: str) -> str:
    """First 12 hex characters of sha1(url). Stable across runs."""
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def normalize_headline(
    *,
    title: str,
    url: str,
    publisher: str,
    published_at: object,
) -> dict | None:
    """One document shape. Empty titles and missing links are dropped."""
    cleaned_title = str(title).strip()
    cleaned_url = str(url).strip()
    if not cleaned_title or not cleaned_url:
        return None
    cleaned_publisher = str(publisher).strip() or "Unknown"
    return {
        "id": headline_id(cleaned_url),
        "source": "news",
        "publisher": cleaned_publisher,
        "title": cleaned_title,
        "url": cleaned_url,
        "published_at": _format_published_at(published_at),
    }


def dedupe_headlines(documents: list[dict]) -> list[dict]:
    """Newest first. A repeated url keeps the newest copy."""
    ordered = sorted(documents, key=lambda document: document["published_at"], reverse=True)
    seen: set[str] = set()
    kept: list[dict] = []
    for document in ordered:
        if document["id"] in seen:
            continue
        seen.add(document["id"])
        kept.append(document)
    return kept


def from_finnhub_item(item: dict) -> dict | None:
    published = item.get("datetime")
    if published is None:
        return None
    return normalize_headline(
        title=str(item.get("headline") or ""),
        url=str(item.get("url") or ""),
        publisher=str(item.get("source") or ""),
        published_at=pd.Timestamp(int(published), unit="s", tz="UTC"),
    )


def from_yfinance_item(item: dict) -> dict | None:
    content = item.get("content")
    payload = content if isinstance(content, dict) else item
    url = _first_url(
        payload.get("canonicalUrl"),
        payload.get("clickThroughUrl"),
        payload.get("link"),
        payload.get("url"),
    )
    published = payload.get("pubDate") or payload.get("providerPublishTime") or item.get("providerPublishTime")
    provider = payload.get("provider") or payload.get("publisher") or item.get("publisher")
    if isinstance(provider, dict):
        publisher = str(provider.get("displayName") or provider.get("name") or "")
    else:
        publisher = str(provider or "")
    if isinstance(published, (int, float)) and not isinstance(published, bool):
        published_at: object = pd.Timestamp(int(published), unit="s", tz="UTC")
    else:
        published_at = published
    return normalize_headline(
        title=str(payload.get("title") or item.get("title") or ""),
        url=url,
        publisher=publisher,
        published_at=published_at,
    )


def from_rss_entry(entry: dict) -> dict | None:
    source = entry.get("source")
    if isinstance(source, dict):
        publisher = str(source.get("title") or "")
    else:
        publisher = "Google News"
    published = entry.get("published") or entry.get("updated")
    if published is None and entry.get("published_parsed"):
        parsed = entry["published_parsed"]
        published = pd.Timestamp(*parsed[:6], tz="UTC")
    return normalize_headline(
        title=str(entry.get("title") or ""),
        url=str(entry.get("link") or ""),
        publisher=publisher,
        published_at=published,
    )


def fetch_headlines(
    symbol: str,
    *,
    now: pd.Timestamp | None = None,
    api_key: str | None = None,
    finnhub: FinnhubFetcher | None = None,
    yahoo: HeadlineFetcher | None = None,
    rss: HeadlineFetcher | None = None,
    lookback_days: int = LOOKBACK_DAYS,
) -> list[dict]:
    """Headlines from the last ``lookback_days``, newest first.

    Finnhub company news is used when an API key is set. Otherwise Yahoo
    Finance, then Google News RSS.
    """
    symbol = symbol.upper()
    as_of = pd.Timestamp.now(tz="UTC") if now is None else _as_utc(now)
    key = read_api_key() if api_key is None else api_key.strip().strip("'\"")
    finnhub_fetcher = finnhub or fetch_finnhub
    yahoo_fetcher = yahoo or fetch_yfinance
    rss_fetcher = rss or fetch_google_news

    documents: list[dict] = []
    if key:
        documents = _call_or_empty(lambda: finnhub_fetcher(symbol, key, as_of))
    if not documents:
        documents = _call_or_empty(lambda: yahoo_fetcher(symbol))
    if not documents:
        documents = _call_or_empty(lambda: rss_fetcher(symbol))

    cutoff = as_of - pd.Timedelta(days=lookback_days)
    recent = [
        document
        for document in documents
        if _as_utc(document["published_at"]) >= cutoff and set(document) >= set(_DOCUMENT_KEYS)
    ]
    return dedupe_headlines(without_junk(recent))


def fetch_finnhub(symbol: str, api_key: str, now: pd.Timestamp) -> list[dict]:
    import requests

    end = _as_utc(now)
    start = end - pd.Timedelta(days=LOOKBACK_DAYS)
    response = requests.get(
        "https://finnhub.io/api/v1/company-news",
        params={
            "symbol": symbol,
            "from": start.date().isoformat(),
            "to": end.date().isoformat(),
            "token": api_key,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return []
    return _parse_each(from_finnhub_item, payload)


def fetch_yfinance(symbol: str) -> list[dict]:
    import yfinance as yf

    items = yf.Ticker(symbol).get_news(count=50) or []
    return _parse_each(from_yfinance_item, items)


def fetch_google_news(symbol: str) -> list[dict]:
    import feedparser

    feedparser.USER_AGENT = "sentifi-research/0.1"
    parsed = feedparser.parse(
        "https://news.google.com/rss/search"
        f"?q={symbol}+when:14d&hl=en-US&gl=US&ceid=US:en"
    )
    return _parse_each(from_rss_entry, parsed.entries)


def read_api_key() -> str:
    """Finnhub key from the environment or a gitignored ``.env`` file."""
    _load_dotenv()
    return os.environ.get("FINNHUB_API_KEY", "").strip().strip("'\"")


def _parse_each(parser: Callable, items) -> list[dict]:
    documents: list[dict] = []
    for item in items:
        try:
            document = parser(item)
        except (TypeError, ValueError, OverflowError):
            continue
        if document is not None:
            documents.append(document)
    return documents


def _call_or_empty(fetcher: Callable[[], list[dict]]) -> list[dict]:
    try:
        return list(fetcher() or [])
    except Exception:  # noqa: BLE001  # a failed source falls through to the next one
        return []


def _format_published_at(value: object) -> str:
    return _as_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _as_utc(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _first_url(*candidates: object) -> str:
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
        if isinstance(candidate, dict):
            url = candidate.get("url")
            if isinstance(url, str) and url.strip():
                return url.strip()
    return ""


def _load_dotenv() -> None:
    path = Path(__file__).resolve().parents[2] / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("'\"")


def scored_news_history(symbol: str, start: date, end: date) -> list[dict]:
    """FinBERT-scored headlines from ``start`` through ``end``, reused from disk.

    The archive is Google News, one week at a time, so each session's lagged score
    has headlines from that week rather than only the tail of a month.
    """
    cache = Path(__file__).resolve().parents[1] / "data" / "news" / f"{symbol}-history.json"
    if cache.exists():
        return without_junk(json.loads(cache.read_text(encoding="utf-8")))
    documents = fetch_news_history(symbol, start, end)
    if not documents:
        return []
    from ml.sentiment.finbert import score_titles
    from ml.sentiment.run import apply_scores

    print(f"{symbol}: scoring {len(documents)} historical headlines", flush=True)
    scores = score_titles([document["title"] for document in documents])
    scored = apply_scores(documents, scores)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(scored) + "\n", encoding="utf-8")
    return scored


def fetch_news_history(symbol: str, start: date, end: date) -> list[dict]:
    """Headlines whose publish day falls inside each week from ``start`` to ``end``."""
    raw_cache = Path(__file__).resolve().parents[1] / "data" / "news" / f"{symbol}-history-raw.json"
    stored = json.loads(raw_cache.read_text(encoding="utf-8")) if raw_cache.exists() else {}
    for week_start, week_end, week_key in _weeks(start, end):
        if week_key in stored:
            continue
        print(f"news history {week_key}", flush=True)
        stored[week_key] = _google_news_between(symbol, week_start, week_end)
        raw_cache.parent.mkdir(parents=True, exist_ok=True)
        raw_cache.write_text(json.dumps(stored) + "\n", encoding="utf-8")
        time.sleep(1)
    documents = [document for chunk in stored.values() for document in chunk]
    return dedupe_headlines(without_junk(documents))


def _weeks(start: date, end: date) -> list[tuple[date, date, str]]:
    weeks: list[tuple[date, date, str]] = []
    cursor = pd.Timestamp(start).normalize()
    last = pd.Timestamp(end).normalize()
    while cursor <= last:
        week_end = min(cursor + pd.Timedelta(days=6), last)
        weeks.append((cursor.date(), week_end.date(), cursor.strftime("%Y-%m-%d")))
        cursor = week_end + pd.Timedelta(days=1)
    return weeks


def _google_news_between(symbol: str, start: date, end: date) -> list[dict]:
    import feedparser

    before = (pd.Timestamp(end) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    after = pd.Timestamp(start).strftime("%Y-%m-%d")
    feedparser.USER_AGENT = "sentifi-research/0.1"
    parsed = feedparser.parse(
        "https://news.google.com/rss/search"
        f"?q={symbol}+after:{after}+before:{before}&hl=en-US&gl=US&ceid=US:en"
    )
    kept: list[dict] = []
    for document in _parse_each(from_rss_entry, parsed.entries):
        published = _as_utc(document["published_at"]).date()
        if start <= published <= end:
            kept.append(document)
    print(f"news history {start} {len(kept)} headlines", flush=True)
    return kept
