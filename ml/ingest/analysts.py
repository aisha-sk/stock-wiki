"""Analyst consensus from Finnhub, or Yahoo Finance when no key is set."""

import hashlib

import pandas as pd

from ml.sentiment.labels import label_for


def analyst_score(
    *,
    strong_buy: int,
    buy: int,
    hold: int,
    sell: int,
    strong_sell: int,
) -> int | None:
    """Contract formula. ``hold`` counts in the denominator only."""
    total = strong_buy + buy + hold + sell + strong_sell
    if total <= 0:
        return None
    raw = 100 * (2 * strong_buy + buy - sell - 2 * strong_sell) / (2 * total)
    return round(raw)


def fetch_analysts(symbol: str, *, api_key: str = "", now: pd.Timestamp | None = None) -> dict | None:
    """One ratings source and its single headline, or ``None`` when counts are missing."""
    as_of = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    rows = _finnhub_rows(symbol, api_key) if api_key else []
    provider = "Finnhub"
    if not rows:
        rows = _yahoo_rows(symbol)
        provider = "Yahoo Finance"
    if not rows:
        return None
    latest = rows[0]
    score = analyst_score(**latest["counts"])
    if score is None:
        return None
    previous = None
    if len(rows) > 1:
        previous = analyst_score(**rows[1]["counts"])
    period_label = latest["label"] or as_of.strftime("%b %Y")
    counts = latest["counts"]
    buy_count = counts["strong_buy"] + counts["buy"]
    sell_count = counts["sell"] + counts["strong_sell"]
    total = sum(counts.values())
    title = f"Consensus: {buy_count} buy, {counts['hold']} hold, {sell_count} sell ({period_label})"
    headline = {
        "id": hashlib.sha1(f"analysts:{symbol}:{period_label}:{title}".encode()).hexdigest()[:12],
        "source": "analysts",
        "publisher": provider,
        "title": title,
        "url": None,
        "published_at": as_of.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "score": score,
        "label": label_for(score),
    }
    source = {
        "source": "analysts",
        "display_name": "Wall Street analysts",
        "score": score,
        "label": label_for(score),
        "doc_count": total,
        "note": f"{total} analysts, {period_label}",
        "method": "ratings",
        "previous_score": previous,
    }
    return {"source": source, "headline": headline}


def _finnhub_rows(symbol: str, api_key: str) -> list[dict]:
    import requests

    response = requests.get(
        "https://finnhub.io/api/v1/stock/recommendation",
        params={"symbol": symbol, "token": api_key},
        timeout=20,
    )
    if response.status_code != 200:
        return []
    payload = response.json()
    if not isinstance(payload, list):
        return []
    rows = []
    for item in payload:
        counts = _counts(item)
        if counts is None:
            continue
        period = str(item.get("period") or "")
        label = ""
        if len(period) >= 7 and period[4] == "-":
            label = pd.Timestamp(period[:10]).strftime("%b %Y")
        rows.append({"counts": counts, "label": label})
    return rows


def _yahoo_rows(symbol: str) -> list[dict]:
    import yfinance as yf

    frame = yf.Ticker(symbol).recommendations
    if frame is None or getattr(frame, "empty", True):
        return []
    rows = []
    for record in frame.to_dict(orient="records"):
        counts = _counts(record)
        if counts is None:
            continue
        rows.append({"counts": counts, "label": ""})
    return rows


def _counts(record: dict) -> dict[str, int] | None:
    lookup = {str(key).lower(): value for key, value in record.items()}
    try:
        return {
            "strong_buy": int(lookup["strongbuy"]),
            "buy": int(lookup["buy"]),
            "hold": int(lookup["hold"]),
            "sell": int(lookup["sell"]),
            "strong_sell": int(lookup["strongsell"]),
        }
    except (KeyError, TypeError, ValueError):
        return None
