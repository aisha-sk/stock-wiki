# Status after Checkpoint 1

Written Sat Oct 10, 2026 for SubaitaM's AI agent (DS/ML lane). It covers what has happened,
what is on `main`, and what to do next. For the rules of the repo read `AGENTS.md`, and for
every JSON shape read `docs/CONTRACT.md`. This file does not repeat them.

## Do this first

Everything is on `main` at commit `fdf3fe0`. Your old branches are stale.

```bash
git checkout main
git pull
python scripts/validate_contracts.py data/artifacts
```

The last command must print `OK ... (3 ticker(s))`.

Do not continue work on `ml/F1-ML-1`, `ml/F1-ML-2`, `ml/F1-ML-3`, `ml/F1-ML-4` or
`ml/f2-ml-3-xgboost`. All of their commits are on `main`. Start every new ticket from a fresh
branch off `main`.

## What happened

| When | What |
|---|---|
| Kickoff | Contract, schemas, example fixtures, validator, plan and 27 tickets were written. SWE is @aisha-sk, DS/ML is @SubaitaM. Gate threshold fixed at 0.52. |
| Flow 1, SWE | FastAPI service (`api/`) and the Next.js dashboard (`web/`): price chart, forecast card, sentiment spectrum, headlines. Merged as #28 to #31. |
| Flow 1, DS/ML | Price ingestion, walk-forward logistic regression, news ingestion with FinBERT, the publisher and pipeline. Also F2-ML-3 (XGBoost, three tickers) ahead of schedule. |
| Merge mix-up | #32 merged into `main`, but #33, #34 and #35 merged into each other's branches, because each PR targeted the previous branch. #37 brought that work onto `main` unchanged. |
| Checkpoint 1 | Passed. The dashboard runs on the real artifacts for TSLA, NVDA and AAPL. Results are on issue #10. |

## What is on `main` now

- `ml/`: `ingest/prices.py`, `ingest/news.py`, `features.py`, `train.py`, `evaluate.py`,
  `sentiment/` (FinBERT, labels, aggregate), `tracking.py` (MLflow logging), `publish.py`,
  `pipeline.py`.
- `data/artifacts/`: `tickers.json`, `stocks/{TSLA,NVDA,AAPL}.json`, `model.json`,
  `forecasts.json`. Generated `2026-10-10T21:00:18Z`. They pass the validator.
- `api/`: serves those files unchanged at `/api/health`, `/api/tickers`, `/api/stocks/{symbol}`.
  It validates each file against strict Pydantic models and returns 503 if a file breaks the
  contract, so an invalid artifact takes the dashboard down for that stock.
- `web/`: the Dashboard tab is complete. Model performance and Alerts are placeholders.

Pipeline entry point, unchanged:

```bash
python -m ml.pipeline --tickers TSLA NVDA AAPL --out data/artifacts
```

## Current results

| Version | Model | Directional accuracy | Status | MLflow run ID |
|---|---|---|---|---|
| 3 | `direction-xgb` (xgboost) | 0.4896 | rejected | present |
| 2 | `direction-lr` (logistic_regression) | 0.4836 | rejected | present |
| 1 | `direction-lr` (logistic_regression) | 0.4777 | rejected | `null` |

- Test set: 672 out-of-sample predictions, 2025-11-11 to 2026-10-02.
- Baselines on the same rows: `always_up` 0.5253, `previous_direction` 0.4747.
- Gate: 0.52. No version passes, so `production` is `null` and every stock's `forecast` is
  `null`. The dashboard shows "No forecast", which is the designed state.
- Sentiment: one source per stock (`news`, 91 to 95 articles), so `gap` is `null`.
- `forecasts.json`: 183 rows, 180 resolved (89 hits, hit rate 0.494), 3 pending.

## Problems found at the checkpoint (DS/ML lane)

1. **Junk headlines.** The news feed includes option-chain and quote pages, for example
   "TSLA Oct 2026 322.500 put (TSLA261009P00322500) stock price, news, quote and history -
   Yahoo Finance UK". They score Neutral and pull the news score toward zero. Filter them in
   `ml/ingest/news.py` before scoring, and add a test with a few of these titles.
2. **Unrounded floats.** Values such as `382.70001220703125` and `0.4895833333333333` are
   published as is. The UI formats them, so this is cosmetic. If you round, use 2 decimals
   for prices and 4 for rates, and keep `quote.change_pct` consistent with the rounded closes
   (the validator recomputes it).
3. **Version 1 has no `mlflow_run_id`.** Fine if it predates tracking. Do not invent one.

## What to do next, in order

| # | Ticket | Notes |
|---|---|---|
| 1 | Headline filter (problem 1 above) | Small. Do it first, it changes every news score. |
| 2 | [F2-ML-4](https://github.com/aisha-sk/stock-wiki/issues/18): Reddit and analyst sources | The biggest product gap. Gives the spectrum three rows and a non-null `gap`. |
| 3 | [F2-ML-1](https://github.com/aisha-sk/stock-wiki/issues/15): MLflow tracking | Partly done in `ml/tracking.py`. Check it against the issue's acceptance criteria. |
| 4 | [F2-ML-2](https://github.com/aisha-sk/stock-wiki/issues/16): gate and registry | Partly done: versions carry `status` and `gate_passed`. Check the promotion rule, that history is appended and never rewritten, and the tests the issue lists. |
| 5 | [F2-ML-3](https://github.com/aisha-sk/stock-wiki/issues/17) | Code is merged. Close the issue once its acceptance criteria are confirmed. |

Read each issue in full before starting: `gh issue view <number>`.

Open decision for the humans: keep the "No forecast" result as is, or spend a time-boxed hour
trying to improve the model (for example with sentiment features). Either way the gate stays
at 0.52 and is not tuned to make a model pass.

## What the SWE side is doing meanwhile

F2-SWE-1 (`/api/model`, `/api/forecasts`), F2-SWE-2 (Model performance page), F2-SWE-3
(loading and error states), F2-SWE-4 (CI). None of it changes the contract or touches `ml/`
or `data/artifacts/`. Once CI lands, every PR runs the validator on `data/artifacts`.

## How to ship a ticket

1. `git checkout main && git pull`
2. `git checkout -b ml/<ticket-id>-short-name`
3. Do the work. Stay inside `ml/` and `data/artifacts/`.
4. Run the pipeline, then `python scripts/validate_contracts.py data/artifacts`, then
   `pytest ml -m "not slow"` and `ruff check ml`.
5. Open a PR **into `main`**, with `Closes #<issue number>` in the body.
6. Merge it with **Create a merge commit** before starting the next ticket.

Do not stack PRs on each other. That is what sent #33 to #35 into the wrong branches.

## Things that must not change without both people agreeing

- Anything in `contracts/` or `docs/CONTRACT.md`: field names, units, enums. If the pipeline
  needs a new field, stop and raise it. See section 4 of `docs/CONTRACT.md`.
- The gate threshold (0.52).
- Files in `api/` and `web/`.

Reminders that matter for F2-ML-4:

- Sentiment scores are integers from -100 to 100. Label thresholds are 20 and -20.
- `sentiment.sources` is ordered `analysts`, `news`, `reddit`. A source with no data is left
  out, not zero-filled.
- Analysts use `method: "ratings"`. Their one headline row has `url: null`.
- `gap` is `null` with fewer than 2 sources. Otherwise `points = max(score) - min(score)`.
- If Reddit returns 403 or 429, omit the source and carry on. Never publish a made-up score.
- No "buy" or "sell" wording in `gap.summary`.

## Next checkpoint

Checkpoint 2 ([#19](https://github.com/aisha-sk/stock-wiki/issues/19)): three tickers and the
Model performance tab on real data, CI green. Planned for Sat 4:30 pm Edmonton, 6:30 pm Toronto.
