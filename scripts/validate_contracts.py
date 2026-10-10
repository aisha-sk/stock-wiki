#!/usr/bin/env python3
"""Validate a data directory against the contract.

    python scripts/validate_contracts.py                    # contracts/examples
    python scripts/validate_contracts.py data/artifacts     # real pipeline output

Checks every file against contracts/schemas/*.schema.json, then the cross-field
rules from docs/CONTRACT.md that JSON Schema cannot express. Exits 1 on any error.
Needs: pip install "jsonschema[format]"
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "contracts" / "schemas"
SOURCE_ORDER = ["analysts", "news", "reddit"]
BULLISH_AT, BEARISH_AT = 20, -20

errors = []


def err(path, msg):
    errors.append(f"{path}: {msg}")


def label_for(score):
    return "bullish" if score >= BULLISH_AT else "bearish" if score <= BEARISH_AT else "neutral"


def load(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        err(path, "file is missing")
    except json.JSONDecodeError as e:
        err(path, f"not valid JSON ({e})")
    return None


def check_schema(data, schema_name, path):
    schema = json.loads((SCHEMAS / schema_name).read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    found = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    for e in found:
        while e.context:  # nullable objects are oneOf[null, object]: report the object's real problem
            e = max(e.context, key=lambda c: (len(c.absolute_path), c.validator != "type"))
        where = "/".join(str(p) for p in e.absolute_path) or "(root)"
        err(path, f"{where}: {e.message}")
    return not found


def check_stock(d, path):
    if path.stem != d["symbol"]:
        err(path, f"file name must be {d['symbol']}.json")
    dates = [p["date"] for p in d["prices"]]
    if dates != sorted(set(dates)):
        err(path, "prices must be ascending by date with no duplicates")
    if dates[-1] != d["quote"]["as_of"]:
        err(path, "quote.as_of must equal the last prices[].date")
    if abs(d["prices"][-1]["close"] - d["quote"]["price"]) > 0.011:
        err(path, "quote.price must equal the last prices[].close")
    prev, last = d["prices"][-2]["close"], d["prices"][-1]["close"]
    if abs((last / prev - 1) * 100 - d["quote"]["change_pct"]) > 0.011:
        err(path, "quote.change_pct must be (last close / previous close - 1) * 100, 2 dp")

    f = d["forecast"]
    if f:
        if (f["direction"] == "up") != (f["prob_up"] >= 0.5):
            err(path, "forecast.direction must be up exactly when prob_up >= 0.5")
        if abs(f["confidence"] - max(f["prob_up"], 1 - f["prob_up"])) > 0.0051:
            err(path, "forecast.confidence must equal max(prob_up, 1 - prob_up)")
        if f["as_of_date"] != d["quote"]["as_of"]:
            err(path, "forecast.as_of_date must equal quote.as_of")

    sources = d["sentiment"]["sources"]
    names = [s["source"] for s in sources]
    if names != [s for s in SOURCE_ORDER if s in names]:
        err(path, "sentiment.sources must be unique and ordered analysts, news, reddit")
    for s in sources:
        if s["label"] != label_for(s["score"]):
            err(path, f"sentiment source {s['source']}: label must be {label_for(s['score'])} for score {s['score']}")
    gap = d["sentiment"]["gap"]
    if (gap is None) != (len(sources) < 2):
        err(path, "sentiment.gap must be null exactly when fewer than 2 sources are present")
    if gap and len(sources) >= 2:
        scores = {s["source"]: s["score"] for s in sources}
        if gap["points"] != max(scores.values()) - min(scores.values()):
            err(path, "sentiment.gap.points must be max(score) - min(score)")
        if scores[gap["most_bullish"]] != max(scores.values()) or scores[gap["most_bearish"]] != min(scores.values()):
            err(path, "sentiment.gap.most_bullish / most_bearish do not match the scores")

    ids = [h["id"] for h in d["headlines"]]
    if len(ids) != len(set(ids)):
        err(path, "headlines[].id must be unique")
    times = [h["published_at"] for h in d["headlines"]]
    if times != sorted(times, reverse=True):
        err(path, "headlines must be newest first")
    for h in d["headlines"]:
        if h["label"] != label_for(h["score"]):
            err(path, f"headline {h['id']}: label must be {label_for(h['score'])} for score {h['score']}")


def check_model(d, path):
    prod_versions = [v for v in d["versions"] if v["status"] == "production"]
    if len(prod_versions) > 1:
        err(path, "at most one version may have status production")
    if (d["production"] is None) != (len(prod_versions) == 0):
        err(path, "production must be null exactly when no version has status production")
    if d["production"] and prod_versions and d["production"]["version"] != prod_versions[0]["version"]:
        err(path, "production.version must match the version with status production")
    gate = d["gate"]
    if gate["passed"] != (d["metrics"][gate["metric"]] >= gate["threshold"]):
        err(path, "gate.passed must equal metrics.directional_accuracy >= gate.threshold")
    for v in d["versions"]:
        if v["gate_passed"] != (v["directional_accuracy"] >= gate["threshold"]):
            err(path, f"version {v['version']}: gate_passed does not match gate.threshold")
        if v["status"] == "rejected" and v["gate_passed"]:
            err(path, f"version {v['version']}: a rejected version cannot have gate_passed true")
        if v["status"] == "production" and not v["gate_passed"]:
            err(path, f"version {v['version']}: the production version must have passed the gate")
    weeks = [w["week_start"] for w in d["weekly_accuracy"]]
    if weeks != sorted(set(weeks)):
        err(path, "weekly_accuracy must be ascending by week_start with no duplicates")


def check_forecasts(d, path, symbols):
    rows = d["forecasts"]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        err(path, "forecasts[].id must be unique")
    if [r["as_of_date"] for r in rows] != sorted((r["as_of_date"] for r in rows), reverse=True):
        err(path, "forecasts must be newest as_of_date first")
    for r in rows:
        if r["id"] != f"{r['symbol']}-{r['as_of_date']}-v{r['model_version']}":
            err(path, f"forecast {r['id']}: id must be {{symbol}}-{{as_of_date}}-v{{model_version}}")
        if symbols and r["symbol"] not in symbols:
            err(path, f"forecast {r['id']}: symbol is not in tickers.json")
        if (r["direction"] == "up") != (r["prob_up"] >= 0.5):
            err(path, f"forecast {r['id']}: direction must be up exactly when prob_up >= 0.5")
        outcome = (r["actual_direction"], r["actual_return_pct"], r["result"])
        if r["status"] == "pending" and any(x is not None for x in outcome):
            err(path, f"forecast {r['id']}: pending rows must have null actual_direction, actual_return_pct, result")
        if r["status"] == "resolved":
            if any(x is None for x in outcome):
                err(path, f"forecast {r['id']}: resolved rows need actual_direction, actual_return_pct, result")
            elif (r["result"] == "hit") != (r["direction"] == r["actual_direction"]):
                err(path, f"forecast {r['id']}: result must be hit exactly when direction == actual_direction")
            elif (r["actual_direction"] == "up") != (r["actual_return_pct"] > 0):
                err(path, f"forecast {r['id']}: actual_direction must be up exactly when actual_return_pct > 0")
    resolved = [r for r in rows if r["status"] == "resolved"]
    hits = sum(r["result"] == "hit" for r in resolved)
    s = d["summary"]
    if (s["resolved"], s["hits"], s["pending"]) != (len(resolved), hits, len(rows) - len(resolved)):
        err(path, "summary counts do not match the forecasts list")
    expected = round(hits / len(resolved), 3) if resolved else None
    if (s["hit_rate"] is None) != (expected is None) or (expected is not None and abs(s["hit_rate"] - expected) > 0.0011):
        err(path, "summary.hit_rate must be hits / resolved (3 dp), or null when resolved is 0")


def main():
    data_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "contracts" / "examples"
    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir

    symbols = []
    tickers = load(data_dir / "tickers.json")
    if tickers is not None and check_schema(tickers, "tickers.schema.json", data_dir / "tickers.json"):
        symbols = [t["symbol"] for t in tickers["tickers"]]

    for sym in symbols:
        path = data_dir / "stocks" / f"{sym}.json"
        stock = load(path)
        if stock is not None and check_schema(stock, "stock.schema.json", path):
            check_stock(stock, path)

    path = data_dir / "model.json"
    model = load(path)
    if model is not None and check_schema(model, "model.schema.json", path):
        check_model(model, path)

    path = data_dir / "forecasts.json"
    forecasts = load(path)
    if forecasts is not None and check_schema(forecasts, "forecasts.schema.json", path):
        check_forecasts(forecasts, path, symbols)

    if errors:
        print(f"FAIL  {len(errors)} contract error(s) in {data_dir}")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"OK    {data_dir} matches the contract ({len(symbols)} ticker(s))")


if __name__ == "__main__":
    main()
