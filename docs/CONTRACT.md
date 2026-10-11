# Data and API contract (v1.1)

This is the single agreement between the ML pipeline, the API and the web app.
If code and this file disagree, this file wins. If this file and
`contracts/schemas/*.schema.json` disagree, the schemas win and this file gets fixed.

## 1. How data moves

```
ml/  ──python -m ml.pipeline──▶  data/artifacts/*.json  ──read + validate──▶  api/  ──HTTP JSON──▶  web/
(DS/ML)                          (committed to git)                          (SWE)                (SWE)

contracts/examples/*.json  =  the same files with fake numbers (is_demo_data: true)
```

- The ML pipeline's only output is four kinds of JSON file. It never talks to the web app.
- The API's response body for a `GET` is the artifact file, unchanged. It adds no fields.
- The API reads from `DATA_DIR`. It defaults to `contracts/examples`, so the web app and API
  work from minute zero. Switching to real data is `DATA_DIR=data/artifacts`, nothing else.
- Run `python scripts/validate_contracts.py data/artifacts` before every push that touches
  artifacts. CI runs it too. A failing validator blocks the merge.

| Artifact file | Served by | Schema |
|---|---|---|
| `tickers.json` | `GET /api/tickers` | `tickers.schema.json` |
| `stocks/{SYMBOL}.json` | `GET /api/stocks/{symbol}` | `stock.schema.json` |
| `model.json` | `GET /api/model` | `model.schema.json` |
| `forecasts.json` | `GET /api/forecasts` | `forecasts.schema.json` |

## 2. Conventions that apply everywhere

| Thing | Rule |
|---|---|
| Key names | `snake_case`. Unknown keys are rejected (`additionalProperties: false`). |
| Missing values | Every key is always present. Use `null`, never omit a key, never `""` or `0` as a stand-in. |
| Timestamps | ISO 8601 UTC with `Z`: `2026-10-09T20:30:00Z`. Keys end in `_at`. |
| Dates | `YYYY-MM-DD`, the US trading session date. Keys end in `_date`, or are `date` / `as_of` / `week_start`. |
| Symbols | Uppercase: `TSLA`. The API upper-cases the path parameter before lookup. |
| Enums | Lowercase strings: `large`, `quiet`, `bullish`, `neutral`, `bearish`, `analysts`, `news`, `reddit`, `direction`, `move`. The UI capitalises for display. |
| Sentiment scores | **Integer from -100 to 100.** Never a 0 to 1 float. |
| Probabilities and rates | **Fraction from 0 to 1** (`prob_large`, `confidence`, `directional_accuracy`, `precision`, `recall`, `f1`, `hit_rate`, `accuracy`, `threshold`). The UI multiplies by 100. `directional_accuracy` is the classification accuracy of that version's `task`. |
| Percent changes | Keys ending in `_pct` are in **percent units**: `1.8` means +1.8%. |
| `max_drawdown` | Negative fraction: `-0.087` means -8.7%. |
| Model version | String of digits: `"12"`. The UI shows `v12`. |
| `is_demo_data` | `true` only in `contracts/examples`. The UI shows a "Demo data" badge whenever it is `true`. Real pipeline output sets `false`. |

### Sentiment label thresholds

```
score >=  20  → "bullish"
score <= -20  → "bearish"
otherwise     → "neutral"
```

The pipeline writes both `score` and `label`. The UI displays `label` and does not recompute it.

### How a score is computed (DS/ML owns this, the UI only needs the result)

- **Text sources (`news`, `reddit`), `method: "finbert"`:** per document,
  `score = round((P(positive) - P(negative)) * 100)`. The source score is the mean of its
  document scores over the last `window_days` days, rounded to an integer.
- **`analysts`, `method: "ratings"`:** from buy/hold/sell counts,
  `score = round(100 * (2*strong_buy + buy - sell - 2*strong_sell) / (2 * total))`.
  This is a ratings consensus, not text sentiment. The Methodology note in the UI must say so.
- A source with no documents in the window is **left out of the array**. It is not zero-filled.
  The agent is not a source.

## 3. Endpoints

Base URL in development: `http://localhost:8000`. All responses are `application/json`.
CORS allows `http://localhost:3000` and the deployed web origin.

| Method and path | Purpose | Success | Errors |
|---|---|---|---|
| `GET /api/health` | Liveness and data freshness | 200 | none |
| `GET /api/tickers` | Stocks the selector offers | 200 | 503 |
| `GET /api/stocks/{symbol}` | Everything on the Dashboard tab | 200 | 404, 503 |
| `GET /api/model` | Everything on the Model performance tab except the log | 200 | 503 |
| `GET /api/forecasts?symbol=&limit=` | Forecast log, Hit/Miss | 200 | 404, 422 |
| `POST /api/alerts` | Create an alert subscription | 201 | 404, 422 |
| `GET /api/alerts/preview?symbol=` | Example email for the Alerts tab | 200 | 404 |
| `POST /api/explain` | Stretch: agent explains the gap, with citations | 200 | 404, 422, 503 |

### Errors

Every non-2xx response has this body. FastAPI's default 422 body is replaced by it.

```json
{ "error": { "code": "not_found", "message": "Unknown symbol: XYZ" } }
```

| Status | `code` | When |
|---|---|---|
| 404 | `not_found` | Symbol is not in `tickers.json` |
| 422 | `validation_error` | Bad query parameter or request body |
| 503 | `data_unavailable` | Artifact file missing, or it fails schema validation |
| 500 | `internal_error` | Anything else |

### GET /api/health

```json
{ "status": "ok", "api_version": "1.0", "data_generated_at": "2026-10-09T21:00:00Z", "is_demo_data": true }
```

`data_generated_at` and `is_demo_data` come from `model.json`.

### GET /api/tickers

```json
{
  "schema_version": "1.1",
  "tickers": [
    { "symbol": "TSLA", "name": "Tesla, Inc." },
    { "symbol": "NVDA", "name": "NVIDIA Corporation" },
    { "symbol": "AAPL", "name": "Apple Inc." }
  ]
}
```

Display order. The first ticker is the default selection.

### GET /api/stocks/{symbol}

Full example: `contracts/examples/stocks/TSLA.json`. Shortened here.

```json
{
  "schema_version": "1.1",
  "symbol": "TSLA",
  "name": "Tesla, Inc.",
  "generated_at": "2026-10-09T21:00:00Z",
  "is_demo_data": true,
  "quote": { "price": 248.31, "change_pct": 1.77, "as_of": "2026-10-09", "currency": "USD" },
  "prices": [
    { "date": "2026-09-14", "close": 231.0 },
    { "date": "2026-10-09", "close": 248.31 }
  ],
  "forecast": {
    "horizon_days": 5,
    "move": "large",
    "prob_large": 0.64,
    "typical_move_pct": 3.2,
    "confidence": 0.64,
    "made_at": "2026-10-09T20:30:00Z",
    "as_of_date": "2026-10-09",
    "target_date": "2026-10-16",
    "model_name": "move-xgb",
    "model_version": "12"
  },
  "sentiment": {
    "window_days": 7,
    "sources": [
      { "source": "analysts", "display_name": "Wall Street analysts", "score": 42, "label": "bullish",
        "doc_count": 38, "note": "38 analysts, Oct 2026", "method": "ratings", "previous_score": 40 },
      { "source": "news", "display_name": "News media", "score": 8, "label": "neutral",
        "doc_count": 142, "note": "142 articles, last 7 days", "method": "finbert", "previous_score": 15 },
      { "source": "reddit", "display_name": "Reddit", "score": -37, "label": "bearish",
        "doc_count": 2100, "note": "2.1k threads, r/stocks and r/wallstreetbets", "method": "finbert", "previous_score": -12 }
    ],
    "gap": { "points": 79, "most_bullish": "analysts", "most_bearish": "reddit",
             "summary": "Wall Street analysts lean bullish while Reddit lean bearish." }
  },
  "headlines": [
    { "id": "3f2a9c1b7e10", "source": "news", "publisher": "Example Wire",
      "title": "Regulators open a review into driver-assist claims",
      "url": "https://example.com/tsla/3f2a9c1b7e10", "published_at": "2026-10-09T11:45:00Z",
      "score": -48, "label": "bearish" }
  ]
}
```

Rules the validator enforces on top of the schema:

| Field | Rule |
|---|---|
| `prices` | 20 to 260 daily closes, ascending, one per trading session, no duplicates |
| `quote.as_of`, `quote.price` | Equal the last `prices` item's `date` and `close` |
| `quote.change_pct` | `(last close / previous close - 1) * 100`, 2 decimals |
| `forecast` | `null` when no model version has passed the gate. The UI must render that state. |
| `forecast.move` | `"large"` exactly when `prob_large >= 0.5` |
| `forecast.typical_move_pct` | Percent units. The median absolute five-session return from the training rows only. |
| `forecast.confidence` | `max(prob_large, 1 - prob_large)`, so always 0.5 to 1 |
| `forecast.as_of_date` | Equals `quote.as_of` |
| `forecast.target_date` | `as_of_date` plus 5 trading sessions |
| `sentiment.sources` | 0 to 3 items, one per source, ordered `analysts`, `news`, `reddit` |
| `sentiment.sources[].previous_score` | Score for the window before this one, or `null` |
| `sentiment.gap` | `null` when fewer than 2 sources. Otherwise `points = max(score) - min(score)` |
| `headlines` | Newest first, at most 30, unique `id`, aim for 2 or more per present source |
| `headlines[].id` | Stable across runs: first 12 hex characters of `sha1(url)` |
| `headlines[].url` | `null` only when there is no link (for example a ratings summary row) |

The forecast does not draw a price path. It says whether the model estimates a move larger than `typical_move_pct`, and it does not say which way.

### GET /api/model

Full example: `contracts/examples/model.json`.

```json
{
  "schema_version": "1.1",
  "generated_at": "2026-10-09T21:00:00Z",
  "is_demo_data": true,
  "production": { "model_name": "move-xgb", "version": "12", "algorithm": "xgboost", "trained_at": "2026-10-04T23:10:00Z" },
  "task": {
    "description": "Will the absolute move over the next 5 sessions be larger than the typical move?",
    "horizon_days": 5, "validation": "walk_forward", "tickers": ["TSLA", "NVDA", "AAPL"],
    "test_start": "2026-07-20", "test_end": "2026-10-09", "n_test": 180
  },
  "metrics": {
    "directional_accuracy": 0.584, "precision": 0.61, "recall": 0.57, "f1": 0.59,
    "sharpe_ratio": null, "max_drawdown": null,
    "inference_latency_ms": 142, "cost_per_request_usd": 0.0004
  },
  "baselines": [
    { "name": "always_quiet", "directional_accuracy": 0.51 },
    { "name": "previous_move", "directional_accuracy": 0.49 }
  ],
  "gate": { "metric": "directional_accuracy", "threshold": 0.52, "passed": true },
  "weekly_accuracy": [ { "week_start": "2026-07-20", "accuracy": 0.571, "n": 15 } ],
  "versions": [
    { "version": "12", "model_name": "move-xgb", "algorithm": "xgboost", "trained_at": "2026-10-04T23:10:00Z",
      "directional_accuracy": 0.584, "gate_passed": true, "status": "production", "mlflow_run_id": "…", "task": "move" },
    { "version": "10", "model_name": "direction-xgb", "algorithm": "xgboost", "trained_at": "2026-09-20T23:10:00Z",
      "directional_accuracy": 0.51, "gate_passed": false, "status": "rejected", "mlflow_run_id": "…", "task": "direction" }
  ]
}
```

| Field | Rule |
|---|---|
| `production` | `null` when no version has `status: "production"` |
| `metrics` | The production version's out-of-sample metrics. If `production` is `null`, the latest candidate's. |
| `metrics.sharpe_ratio`, `max_drawdown`, `inference_latency_ms`, `cost_per_request_usd` | Nullable. The UI shows "—" for `null`. `cost_per_request_usd` is `null` for a locally run model. |
| `precision`, `recall`, `f1` | Positive class is `large` |
| `baselines` | Scored on the same test rows as `metrics` |
| `gate.threshold` | The UI draws the dashed line from this value. It is never hardcoded in the UI. |
| `gate.passed` | Every check in `ml/gate.py` passes. Today: `directional_accuracy >= gate.threshold` and above the `always_quiet` baseline. `passed` is never true below the threshold. |
| `weekly_accuracy` | Last 12 weeks at most, ascending, `week_start` is a Monday |
| `versions` | Newest first, at most one `production`. `status`: `production`, `archived` (passed, since replaced), `rejected` (failed the gate, never served) |

### GET /api/forecasts

Query parameters: `symbol` (optional, filters), `limit` (optional, integer 1 to 200, default 50).
The API filters by symbol, recomputes `summary` over the filtered rows, then applies `limit`.

```json
{
  "schema_version": "1.1",
  "generated_at": "2026-10-09T21:00:00Z",
  "is_demo_data": true,
  "summary": { "resolved": 6, "hits": 4, "hit_rate": 0.667, "pending": 3 },
  "forecasts": [
    { "id": "TSLA-2026-10-09-v12", "symbol": "TSLA", "made_at": "2026-10-09T20:30:00Z",
      "as_of_date": "2026-10-09", "target_date": "2026-10-16", "horizon_days": 5,
      "move": "large", "prob_large": 0.64, "typical_move_pct": 3.2, "model_version": "12", "origin": "live",
      "status": "pending", "actual_move": null, "actual_return_pct": null, "result": null },
    { "id": "TSLA-2026-09-28-v12", "symbol": "TSLA", "made_at": "2026-09-28T20:30:00Z",
      "as_of_date": "2026-09-28", "target_date": "2026-10-05", "horizon_days": 5,
      "move": "large", "prob_large": 0.61, "typical_move_pct": 3.2, "model_version": "12", "origin": "backtest",
      "status": "resolved", "actual_move": "quiet", "actual_return_pct": 3.1, "result": "miss" }
  ]
}
```

| Field | Rule |
|---|---|
| `id` | `{symbol}-{as_of_date}-v{model_version}`, unique |
| `origin` | `backtest`: an out-of-sample walk-forward prediction. `live`: written before the outcome existed. The UI shows the origin, because only `live` rows are a true track record. |
| `status: "pending"` | `actual_move`, `actual_return_pct`, `result` are all `null` |
| `status: "resolved"` | All three are set. `result` is `hit` exactly when `move == actual_move`. `actual_move` is `large` exactly when `abs(actual_return_pct) > typical_move_pct`. |
| Order | Newest `as_of_date` first |
| `summary.hit_rate` | `hits / resolved`, 3 decimals, `null` when `resolved` is 0 |

A live forecast needs 5 trading days to resolve, so on day one every Hit/Miss row has
`origin: "backtest"`. That is expected and the UI labels it.

### POST /api/alerts

Request:

```json
{ "email": "you@example.com", "symbol": "TSLA", "trigger": "sharp_shift" }
```

`trigger` is one of `sharp_shift`, `any_flip`, `weekly_digest`.

Response `201`:

```json
{ "id": "0b9c5e0e-6c1f-4a53-9a43-0f6c2f7f1d11", "email": "you@example.com", "symbol": "TSLA",
  "trigger": "sharp_shift", "created_at": "2026-10-10T01:12:00Z", "delivery": "mock" }
```

Subscriptions are stored in SQLite (`api/alerts.db`, gitignored). `delivery` is `mock` until real
email exists. Posting the same email, symbol and trigger twice returns the existing row with `200`.

### GET /api/alerts/preview?symbol=TSLA

Built by the API from that symbol's stock payload. No artifact file.

```json
{
  "symbol": "TSLA",
  "subject": "TSLA sentiment gap: 79 points",
  "body_lines": [
    "Reddit sentiment moved from -12 to -37 over the last 7 days, while Wall Street analysts stayed at +42.",
    "Model forecast, next 5 trading days: Up, 64% confidence."
  ],
  "is_demo_data": true
}
```

The first line uses the source with the largest `abs(score - previous_score)`. Sources whose
`previous_score` is `null` are skipped. The forecast line is dropped when `forecast` is `null`.

### POST /api/explain (stretch, Flow 3)

Request:

```json
{ "symbol": "TSLA", "question": "Why do analysts and Reddit disagree?" }
```

Response `200`:

```json
{
  "symbol": "TSLA",
  "answer": "Analysts are reacting to delivery numbers, while Reddit threads focus on margins…",
  "citations": [ { "headline_id": "3f2a9c1b7e10", "title": "Regulators open a review into driver-assist claims", "url": "https://example.com/…" } ],
  "model": "claude-opus-5-5",
  "generated_at": "2026-10-10T18:00:00Z"
}
```

Every `headline_id` must exist in that symbol's `headlines`. An answer with zero citations is
returned as `503 data_unavailable`. Without `ANTHROPIC_API_KEY` the endpoint returns `503` and the
UI replaces the panel with a note that the explainer is not set up.

## 4. Changing the contract

1. Say it in chat first. A contract change blocks the other person.
2. One PR, labelled `contract-change`, that updates the schema, the example fixture and this file together.
3. `python scripts/validate_contracts.py` passes on `contracts/examples`.
4. The other person approves before merge. No self-merge on this label.
5. Adding a field is a minor change. Renaming or removing one, or changing a unit, bumps
   `schema_version` and needs both sides ready on the same merge.

## 5. Fixed values both sides rely on

| Name | Value |
|---|---|
| API port | 8000 |
| Web port | 3000 |
| MLflow UI port | 5001 (5000 is taken by AirPlay on macOS) |
| `DATA_DIR` | default `contracts/examples`, real `data/artifacts`, resolved from the repo root |
| `NEXT_PUBLIC_API_URL` | default `http://localhost:8000` |
| Tickers | `TSLA` (Flow 1), then `NVDA`, `AAPL` (Flow 2) |
| Forecast horizon | 5 trading days |
| Sentiment window | 7 days |
| Pipeline entry point | `python -m ml.pipeline --tickers TSLA NVDA AAPL --out data/artifacts` |
