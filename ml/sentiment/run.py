"""Score headlines and print the news source summary."""

import argparse

import pandas as pd

from ml.sentiment.labels import label_for


def apply_scores(documents: list[dict], scores: list[int]) -> list[dict]:
    """Attach an integer score and the contract label. Order is preserved."""
    if len(documents) != len(scores):
        raise ValueError("scores and documents have different lengths")
    scored: list[dict] = []
    for document, score in zip(documents, scores):
        value = max(-100, min(100, int(score)))
        scored.append({**document, "score": value, "label": label_for(value)})
    return scored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score recent news headlines with FinBERT.")
    parser.add_argument("--tickers", nargs="+", required=True)
    args = parser.parse_args(argv)

    from ml.config import load_config
    from ml.ingest.news import fetch_headlines
    from ml.sentiment.aggregate import aggregate_news
    from ml.sentiment.finbert import score_titles

    window_days = load_config().sentiment_window_days
    now = pd.Timestamp.now(tz="UTC")
    for symbol in args.tickers:
        documents = fetch_headlines(symbol, now=now)
        scores = score_titles([document["title"] for document in documents])
        scored = apply_scores(documents, scores)
        summary = aggregate_news(scored, now=now, window_days=window_days)
        name = symbol.upper()
        if summary is None:
            print(f"{name}: no news in the last {window_days} days (fetched {len(scored)})")
            continue
        print(f"{name}: score={summary['score']} doc_count={summary['doc_count']}")
        print(summary["note"])
        for item in scored[:5]:
            print(f"  {item['score']:+d}  {item['label']:<8}  {item['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
