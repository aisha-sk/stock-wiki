"""Run prices, the direction model, news sentiment and the contract publisher."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from ml.config import load_config
from ml.ingest.news import dedupe_headlines, fetch_headlines, scored_news_history
from ml.ingest.prices import load_prices
from ml.publish import (
    MODEL_VERSION,
    median_latency_ms,
    write_artifacts,
)
from ml.sentiment.aggregate import aggregate_news
from ml.sentiment.run import apply_scores
from ml.train import walk_forward


def run_pipeline(symbols: list[str], out_dir: Path) -> int:
    """Build artifacts for ``symbols`` and validate them. Returns the validator status."""
    config = load_config()
    names = {ticker.symbol: ticker.name for ticker in config.tickers}
    missing = [symbol for symbol in symbols if symbol not in names]
    if missing:
        raise SystemExit(f"unknown ticker(s) {missing}; names live in ml/config.yaml")
    generated_at = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    now = pd.Timestamp(generated_at)

    prices: dict[str, pd.DataFrame] = {}
    predictions: dict[str, pd.DataFrame] = {}
    live_prob: dict[str, float] = {}
    headlines: dict[str, list[dict]] = {}
    sources: dict[str, dict | None] = {}
    metrics: dict[str, float | int] | None = None
    baselines: list[dict[str, float | str]] | None = None
    latency_ms = 0.0

    for symbol in symbols:
        frame = load_prices(symbol)
        history_start = pd.Timestamp(frame["date"].min()).date()
        recent = _scored_headlines(symbol, now)
        history = _merge_documents(
            scored_news_history(symbol, history_start, now.date()),
            recent,
        )
        print(f"{symbol}: {len(history)} historical headlines for news_lag1", flush=True)
        trained = walk_forward(
            frame,
            symbol=symbol,
            horizon=config.horizon_days,
            news_documents=history or None,
        )
        row = trained.latest_features
        latency_ms = median_latency_ms(lambda row=row, model=trained.model: model.predict_proba(row))
        prices[symbol] = frame
        predictions[symbol] = trained.predictions
        live_prob[symbol] = float(trained.forecast["prob_up"])
        headlines[symbol] = recent
        sources[symbol] = aggregate_news(recent, now=now, window_days=config.sentiment_window_days)
        metrics = trained.metrics
        baselines = trained.baselines

    if metrics is None or baselines is None:
        raise SystemExit("pipeline needs at least one ticker")
    accuracy = float(metrics["directional_accuracy"])
    threshold = config.gate_threshold
    if accuracy >= threshold:
        print(
            f"Gate passed: directional_accuracy {accuracy:.3f} >= {threshold:.2f}. "
            f"Serving {MODEL_VERSION}.",
            flush=True,
        )
    else:
        print(
            f"Gate failed: directional_accuracy {accuracy:.3f} is below {threshold:.2f}. "
            "production is null and each stock forecast is null.",
            flush=True,
        )
    write_artifacts(
        out_dir,
        symbols=symbols,
        names=names,
        prices=prices,
        predictions=predictions,
        live_prob=live_prob,
        metrics=metrics,
        baselines=baselines,
        gate_threshold=threshold,
        headlines=headlines,
        sources=sources,
        window_days=config.sentiment_window_days,
        prices_in_payload=config.prices_in_payload,
        generated_at=generated_at,
        latency_ms=latency_ms,
    )
    script = Path(__file__).resolve().parents[1] / "scripts" / "validate_contracts.py"
    completed = subprocess.run([sys.executable, str(script), str(out_dir)], check=False)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish contract artifacts for the API.")
    parser.add_argument("--tickers", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = Path.cwd() / out_dir
    return run_pipeline([symbol.upper() for symbol in args.tickers], out_dir)


def _merge_documents(history: list[dict], recent: list[dict]) -> list[dict]:
    """History fills the walk-forward window. Recent headlines cover the last sessions."""
    return dedupe_headlines([*history, *recent])


def _scored_headlines(symbol: str, now: pd.Timestamp) -> list[dict]:
    """Score titles once and reuse the file on a later run the same checkout."""
    cache = Path(__file__).resolve().parent / "data" / "news" / f"{symbol}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    from ml.sentiment.finbert import score_titles

    documents = fetch_headlines(symbol, now=now)
    scores = score_titles([document["title"] for document in documents])
    scored = apply_scores(documents, scores)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(scored, indent=2) + "\n", encoding="utf-8")
    return scored


if __name__ == "__main__":
    raise SystemExit(main())
