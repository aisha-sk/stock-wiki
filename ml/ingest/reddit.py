"""Reddit search RSS for the three default investing subreddits."""

import os
import time

import feedparser
import pandas as pd
import requests

from ml.ingest.news import normalize_headline, read_api_key

SUBREDDITS = ("wallstreetbets", "stocks", "investing")
_PAUSE_SECONDS = 2


def fetch_reddit(symbol: str, company_name: str) -> list[dict] | None:
    """Matching posts, or ``None`` when Reddit answers 403 or 429.

    ``None`` tells the publisher to omit the source. A 429 is not retried.
    """
    read_api_key()
    agent = os.environ.get("REDDIT_USER_AGENT", "sentifi-research/0.1").strip() or "sentifi-research/0.1"
    documents: list[dict] = []
    for subreddit in SUBREDDITS:
        time.sleep(_PAUSE_SECONDS)
        response = requests.get(
            f"https://www.reddit.com/r/{subreddit}/search.rss",
            params={"q": symbol, "restrict_sr": 1, "sort": "new", "t": "week"},
            headers={"User-Agent": agent},
            timeout=20,
        )
        if response.status_code in {403, 429}:
            print(f"reddit {symbol} r/{subreddit} HTTP {response.status_code}; omitting reddit", flush=True)
            return None
        if response.status_code != 200 or not response.text.lstrip().startswith("<"):
            continue
        parsed = feedparser.parse(response.text)
        for entry in parsed.entries:
            title = str(entry.get("title") or "")
            if not _mentions(title, symbol, company_name):
                continue
            document = normalize_headline(
                title=title,
                url=str(entry.get("link") or ""),
                publisher=f"r/{subreddit}",
                published_at=entry.get("published") or entry.get("updated") or pd.Timestamp.now(tz="UTC"),
            )
            if document is not None:
                document["source"] = "reddit"
                documents.append(document)
    return documents


def _mentions(title: str, symbol: str, company_name: str) -> bool:
    text = title.lower()
    if f" {symbol.lower()} " in f" {text} ":
        return True
    name = company_name.split(",")[0].strip().lower()
    return bool(name) and name in text
