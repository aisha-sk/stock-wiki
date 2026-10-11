"""Run prices, the direction model, news sentiment and the contract publisher."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

from ml.config import load_config
from ml.features import FEATURE_COLUMNS, NEWS_LAG_COLUMN
from ml.gate import failed_checks, passes_gate
from ml.ingest.analysts import fetch_analysts
from ml.ingest.news import (
    dedupe_headlines,
    fetch_headlines,
    read_api_key,
    scored_news_history,
    without_junk,
)
from ml.ingest.prices import load_prices
from ml.ingest.reddit import fetch_reddit
from ml.publish import median_latency_ms, write_artifacts
from ml.registry import append_version, register_mlflow_model
from ml.sentiment.aggregate import aggregate_news, aggregate_posts
from ml.sentiment.run import apply_scores
from ml.tracking import log_candidate
from ml.train import (
    ALGORITHMS,
    INITIAL_SESSIONS,
    PURGE,
    TEST_BLOCK,
    XGB_PARAMS,
    format_report,
    walk_forward_pooled,
)


def run_pipeline(symbols: list[str], out_dir: Path, train: bool = True) -> int:
    """Build artifacts for ``symbols`` and validate them. Returns the validator status.

    ``train=False`` refreshes prices, sentiment and forecasts but registers no version and
    leaves ``model.json`` as it was.
    """
    model_path = out_dir / "model.json"
    if not train and not model_path.exists():
        raise SystemExit(f"--no-train needs an existing {model_path}")
    prior_model = None if train else model_path.read_text(encoding="utf-8")
    config = load_config()
    names = {ticker.symbol: ticker.name for ticker in config.tickers}
    missing = [symbol for symbol in symbols if symbol not in names]
    if missing:
        raise SystemExit(f"unknown ticker(s) {missing}; names live in ml/config.yaml")
    generated_at = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
    now = pd.Timestamp(generated_at)

    ordered = [ticker.symbol for ticker in config.tickers if ticker.symbol in set(symbols)]
    prices: dict[str, pd.DataFrame] = {}
    headlines: dict[str, list[dict]] = {}
    sources: dict[str, list[dict]] = {}
    news: dict[str, list[dict]] = {}
    for symbol in ordered:
        frame = load_prices(symbol)
        history_start = pd.Timestamp(frame["date"].min()).date()
        recent = _scored_headlines(symbol, now)
        history = _merge_documents(
            scored_news_history(symbol, history_start, now.date()),
            recent,
        )
        print(f"{symbol}: {len(history)} historical headlines for news_lag1", flush=True)
        prices[symbol] = frame
        news[symbol] = history
        company = names[symbol]
        bundle = _sentiment_bundle(symbol, company, recent, now, config.sentiment_window_days)
        headlines[symbol] = bundle["headlines"]
        sources[symbol] = bundle["sources"]

    candidates = []
    for algorithm in ALGORITHMS:
        trained = walk_forward_pooled(
            prices,
            horizon=config.horizon_days,
            news_documents=news,
            algorithm=algorithm,
        )
        params = dict(XGB_PARAMS)
        data_end = max(pd.Timestamp(frame["date"].max()) for frame in prices.values())
        if not train:
            candidates.append((algorithm, trained, None))
            continue
        run_id = log_candidate(
            algorithm=algorithm,
            params=params,
            metrics=trained.metrics,
            baselines=trained.baselines,
            predictions=trained.predictions,
            model=trained.model,
            feature_names=[*FEATURE_COLUMNS, NEWS_LAG_COLUMN],
            tickers=ordered,
            horizon=config.horizon_days,
            initial_window=INITIAL_SESSIONS,
            test_block=TEST_BLOCK,
            purge=PURGE,
            data_end=data_end.strftime("%Y-%m-%d"),
            gate_threshold=config.gate_threshold,
        )
        print(format_report(algorithm, trained.metrics, trained.baselines), flush=True)
        candidates.append((algorithm, trained, run_id))

    threshold = config.gate_threshold
    passed = [
        item
        for item in candidates
        if passes_gate(item[1].metrics, threshold, item[1].baselines)
    ]
    if passed:
        serving = max(passed, key=lambda item: float(item[1].metrics["directional_accuracy"]))
    else:
        serving = candidates[-1]
    algorithm, trained, run_id = serving
    accuracy = round(float(trained.metrics["directional_accuracy"]), 4)
    failures = failed_checks(trained.metrics, threshold, trained.baselines)
    if not train:
        pass
    elif not failures:
        print(f"Gate passed: {algorithm} directional_accuracy {accuracy:.4f}.", flush=True)
    else:
        print("REJECTED", flush=True)
        print(
            f"Gate failed: {algorithm} directional_accuracy {accuracy:.4f} fails "
            f"{'; '.join(failures)}. production is null and each stock forecast is null.",
            flush=True,
        )

    history = _prior_versions(out_dir)
    gate_passed = None
    if train:
        for name, result, candidate_run in candidates:
            history = append_version(
                history,
                accuracy=float(result.metrics["directional_accuracy"]),
                threshold=threshold,
                baselines=result.baselines,
                algorithm=name,
                model_name="move-xgb",
                trained_at=generated_at,
                mlflow_run_id=candidate_run,
            )
            register_mlflow_model(candidate_run)
        fresh = [item for item in history if item["trained_at"] == generated_at]
        serving_version = fresh[0]["version"] if fresh else history[0]["version"]
    else:
        # shortcut: refits the fixed-parameter model on today's data instead of loading the
        # promoted binary (binaries stay out of git); upgrade with a registry CI can read.
        production = json.loads(prior_model)["production"]
        serving_version = production["version"] if production else history[0]["version"]
        gate_passed = production is not None
        print(f"--no-train: serving version {serving_version}, gate_passed {gate_passed}.")
    sample = trained.latest_features[ordered[0]]
    latency_ms = median_latency_ms(lambda row=sample, model=trained.model: model.predict_proba(row))
    write_artifacts(
        out_dir,
        symbols=ordered,
        names=names,
        prices=prices,
        predictions={symbol: trained.predictions[trained.predictions["symbol"] == symbol] for symbol in ordered},
        live_prob={symbol: float(trained.forecasts[symbol]["prob_large"]) for symbol in ordered},
        typical_move_pct={
            symbol: float(trained.forecasts[symbol]["typical_move_pct"]) for symbol in ordered
        },
        metrics=trained.metrics,
        baselines=trained.baselines,
        gate_threshold=threshold,
        headlines=headlines,
        sources=sources,
        window_days=config.sentiment_window_days,
        prices_in_payload=config.prices_in_payload,
        generated_at=generated_at,
        latency_ms=latency_ms,
        sharpe_ratio=None,
        max_drawdown=None,
        model_name="move-xgb",
        model_version=serving_version,
        algorithm=algorithm,
        mlflow_run_id=run_id,
        versions=history,
        gate_passed=gate_passed,
    )
    if prior_model is not None:
        model_path.write_text(prior_model, encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "scripts" / "validate_contracts.py"
    completed = subprocess.run([sys.executable, str(script), str(out_dir)], check=False)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish contract artifacts for the API.")
    parser.add_argument("--tickers", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--no-train",
        action="store_true",
        help="refresh data and forecasts without registering a version or changing model.json",
    )
    args = parser.parse_args(argv)
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = Path.cwd() / out_dir
    return run_pipeline(
        [symbol.upper() for symbol in args.tickers], out_dir, train=not args.no_train
    )


# Reddit's Responsible Builder Policy requires explicit approval before any access to Reddit
# data, including the public search feeds. We do not have it, so the fetch is off. Set
# REDDIT_ENABLED=1 only after access has been approved.
REDDIT_ENABLED = os.environ.get("REDDIT_ENABLED") == "1"


def _sentiment_bundle(
    symbol: str,
    company: str,
    news_documents: list[dict],
    now: pd.Timestamp,
    window_days: int,
) -> dict:
    """Analysts, news and Reddit. A missing group is left out. The agent is not a source."""
    present: list[dict] = []
    groups: list[list[dict]] = []
    news_source = aggregate_news(news_documents, now=now, window_days=window_days)
    if news_source is not None:
        present.append(news_source)
        groups.append(news_documents)
    reddit_documents = fetch_reddit(symbol, company) if REDDIT_ENABLED else []
    if reddit_documents:
        from ml.sentiment.finbert import score_titles

        scores = score_titles([document["title"] for document in reddit_documents])
        scored = apply_scores(reddit_documents, scores)
        reddit_source = aggregate_posts(
            scored,
            source="reddit",
            display_name="Reddit",
            now=now,
            window_days=window_days,
            noun="thread",
            note=_reddit_note(scored, now, window_days),
        )
        if reddit_source is not None:
            present.append(reddit_source)
            groups.append(scored)
    analyst = fetch_analysts(symbol, api_key=read_api_key(), now=now)
    if analyst is not None:
        present.append(analyst["source"])
        groups.append([analyst["headline"]])
    order = {"analysts": 0, "news": 1, "reddit": 2}
    present.sort(key=lambda source: order[source["source"]])
    return {"sources": present, "headlines": _mix_headlines(groups)}


def _reddit_note(documents: list[dict], now: pd.Timestamp, window_days: int) -> str:
    start = pd.Timestamp(now) - pd.Timedelta(days=window_days)
    current = [
        document
        for document in documents
        if start <= pd.Timestamp(document["published_at"]) <= pd.Timestamp(now)
    ]
    subs: list[str] = []
    for document in current:
        publisher = str(document["publisher"])
        if publisher not in subs:
            subs.append(publisher)
    if len(subs) <= 1:
        where = subs[0] if subs else "Reddit"
    else:
        where = ", ".join(subs[:-1]) + " and " + subs[-1]
    noun = "thread" if len(current) == 1 else "threads"
    return f"{len(current)} {noun}, {where}"


def _mix_headlines(groups: list[list[dict]], limit: int = 30) -> list[dict]:
    """Keep at least two headlines from each group, then fill by recency."""
    protected: list[dict] = []
    seen: set[str] = set()
    for group in groups:
        for document in sorted(group, key=lambda item: item["published_at"], reverse=True)[:2]:
            if document["id"] not in seen:
                protected.append(document)
                seen.add(document["id"])
    rest = [
        document
        for group in groups
        for document in group
        if document["id"] not in seen
    ]
    mixed = protected + rest
    mixed.sort(key=lambda item: item["published_at"], reverse=True)
    return mixed[:limit]


def _prior_versions(out_dir: Path) -> list[dict]:
    """Registry rows already on disk. This run appends; it does not rewrite them."""
    path = out_dir / "model.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    versions = payload.get("versions")
    return list(versions) if isinstance(versions, list) else []


def _merge_documents(history: list[dict], recent: list[dict]) -> list[dict]:
    """History fills the walk-forward window. Recent headlines cover the last sessions."""
    return dedupe_headlines([*history, *recent])


def _scored_headlines(symbol: str, now: pd.Timestamp) -> list[dict]:
    """Score titles once and reuse the file on a later run the same checkout."""
    cache = Path(__file__).resolve().parent / "data" / "news" / f"{symbol}.json"
    if cache.exists():
        return without_junk(json.loads(cache.read_text(encoding="utf-8")))
    from ml.sentiment.finbert import score_titles

    documents = fetch_headlines(symbol, now=now)
    scores = score_titles([document["title"] for document in documents])
    scored = apply_scores(documents, scores)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(scored, indent=2) + "\n", encoding="utf-8")
    return scored


if __name__ == "__main__":
    raise SystemExit(main())
