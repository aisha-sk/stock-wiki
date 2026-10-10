"""Run prices, the direction model, news sentiment and the contract publisher."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from ml.config import load_config
from ml.evaluate import strategy_backtest
from ml.ingest.news import dedupe_headlines, fetch_headlines, scored_news_history
from ml.ingest.prices import load_prices
from ml.publish import median_latency_ms, write_artifacts
from ml.sentiment.aggregate import aggregate_news
from ml.sentiment.run import apply_scores
from ml.tracking import log_candidate
from ml.train import ALGORITHMS, XGB_PARAMS, format_report, walk_forward_pooled


def run_pipeline(symbols: list[str], out_dir: Path) -> int:
    """Build artifacts for ``symbols`` and validate them. Returns the validator status."""
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
    sources: dict[str, dict | None] = {}
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
        headlines[symbol] = recent
        news[symbol] = history
        sources[symbol] = aggregate_news(recent, now=now, window_days=config.sentiment_window_days)

    candidates = []
    for algorithm in ALGORITHMS:
        trained = walk_forward_pooled(
            prices,
            horizon=config.horizon_days,
            news_documents=news,
            algorithm=algorithm,
        )
        params = dict(XGB_PARAMS)
        run_id = log_candidate(algorithm=algorithm, params=params, metrics=trained.metrics)
        print(format_report(algorithm, trained.metrics, trained.baselines), flush=True)
        candidates.append((algorithm, trained, run_id))

    threshold = config.gate_threshold
    passed = [
        item
        for item in candidates
        if float(item[1].metrics["directional_accuracy"]) >= threshold
    ]
    if passed:
        serving = max(passed, key=lambda item: float(item[1].metrics["directional_accuracy"]))
    else:
        serving = candidates[-1]
    algorithm, trained, run_id = serving
    accuracy = float(trained.metrics["directional_accuracy"])
    if accuracy >= threshold:
        print(
            f"Gate passed: {algorithm} directional_accuracy {accuracy:.3f} >= {threshold:.2f}.",
            flush=True,
        )
    else:
        print(
            f"Gate failed: {algorithm} directional_accuracy {accuracy:.3f} is below {threshold:.2f}. "
            "production is null and each stock forecast is null.",
            flush=True,
        )

    prior = _prior_versions(out_dir)
    next_version = 1 + max((int(item["version"]) for item in prior), default=0)
    recorded = []
    for offset, (name, result, candidate_run) in enumerate(candidates):
        candidate_accuracy = float(result.metrics["directional_accuracy"])
        is_serving = result is trained
        gate_passed = candidate_accuracy >= threshold
        if is_serving and gate_passed:
            status = "production"
        elif gate_passed:
            status = "archived"
        else:
            status = "rejected"
        recorded.append(
            {
                "version": str(next_version + offset),
                "model_name": "direction-xgb",
                "algorithm": name,
                "trained_at": generated_at,
                "directional_accuracy": candidate_accuracy,
                "gate_passed": gate_passed,
                "status": status,
                "mlflow_run_id": candidate_run,
            }
        )
    recorded.reverse()
    serving_version = next(
        item["version"] for item in recorded if item["algorithm"] == algorithm and item["trained_at"] == generated_at
    )
    sample = trained.latest_features[ordered[0]]
    latency_ms = median_latency_ms(lambda row=sample, model=trained.model: model.predict_proba(row))
    backtest = strategy_backtest(trained.predictions)
    write_artifacts(
        out_dir,
        symbols=ordered,
        names=names,
        prices=prices,
        predictions={symbol: trained.predictions[trained.predictions["symbol"] == symbol] for symbol in ordered},
        live_prob={symbol: float(trained.forecasts[symbol]["prob_up"]) for symbol in ordered},
        metrics=trained.metrics,
        baselines=trained.baselines,
        gate_threshold=threshold,
        headlines=headlines,
        sources=sources,
        window_days=config.sentiment_window_days,
        prices_in_payload=config.prices_in_payload,
        generated_at=generated_at,
        latency_ms=latency_ms,
        sharpe_ratio=backtest["sharpe_ratio"],
        max_drawdown=backtest["max_drawdown"],
        model_name="direction-xgb",
        model_version=serving_version,
        algorithm=algorithm,
        mlflow_run_id=run_id,
        versions=[*recorded, *prior],
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
