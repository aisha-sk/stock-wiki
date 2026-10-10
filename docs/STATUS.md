# Status: Flow 2 SWE merged, Checkpoint 2 pending

Updated Sat Oct 10, 2026 for SubaitaM's AI agent (DS/ML lane). It covers what changed since
Checkpoint 1, what is on `main`, and what to do next. For the rules of the repo read
`AGENTS.md`, and for every JSON shape read `docs/CONTRACT.md`. This file does not repeat them.

## Do this first

```bash
git checkout main
git pull
python scripts/validate_contracts.py data/artifacts
```

The last command must print `OK ... (3 ticker(s))`. `main` is at `aa31d4c` plus this file.
Start every new ticket from a fresh branch off `main`. All older `ml/*` branches are merged
and stale.

## What changed since Checkpoint 1

| Who | What | PR |
|---|---|---|
| DS/ML | Headline filter: option-chain and quote pages dropped; published figures rounded | #41 |
| DS/ML | F2-ML-4: analyst ratings and Reddit ingestion, gap computation | #43 |
| SWE | F2-SWE-1: `GET /api/model`, `GET /api/forecasts` | #38 |
| SWE | F2-SWE-2: Model performance page | #39 |
| SWE | F2-SWE-3: loading, error and empty states | #40 |
| SWE | F2-SWE-4: CI on every PR and on `main` | #42 |

All SWE Flow 2 tickets are done and closed. CI is green on `main`.

## CI now runs on your PRs

`.github/workflows/ci.yml` runs four jobs on every pull request:

| Job | What it runs | What it means for DS/ML |
|---|---|---|
| Contract validation | `scripts/validate_contracts.py` on the fixtures and on `data/artifacts` | A PR whose artifacts break the contract fails. Run the validator before pushing. |
| ML | `ruff check ml`, `pytest ml -m "not slow"` | Uses a light package list written in the workflow: pandas, numpy, scikit-learn, xgboost, yfinance, pandas_market_calendars, pyyaml, jsonschema, pyarrow, feedparser, requests. torch, transformers and mlflow are **not** installed. |
| API | `ruff`, `pytest` | Not your lane. |
| Web | lint, type check, build | Not your lane. |

If a fast ML test needs a new package, either import it lazily inside the function (as
`mlflow`, `feedparser` and `requests` are now) or ask SWE to add it to the workflow's list.
A test that needs torch must be marked `@pytest.mark.slow`.

## What the app shows on the current artifacts

Artifacts generated `2026-10-10T21:57:39Z`. They pass the validator.

| Stock | Analysts | News | Reddit | Gap |
|---|---|---|---|---|
| TSLA | +19 neutral (44 analysts) | +22 bullish (51 articles) | missing | 3 |
| NVDA | +55 bullish (62 analysts) | +15 neutral (69 articles) | missing | 40 |
| AAPL | +25 bullish (44 analysts) | +8 neutral (52 articles) | missing | 17 |

| Version | Model | Directional accuracy | Status |
|---|---|---|---|
| 5 | `direction-xgb` | 0.4955 | rejected |
| 4 | `direction-xgb` | 0.4955 | rejected |
| 3 | `direction-xgb` | 0.4896 | rejected |
| 2 | `direction-lr` | 0.4836 | rejected |
| 1 | `direction-lr` | 0.4777 | rejected |

- Baselines: `always_up` 0.5253, `previous_direction` 0.4747, over 672 test forecasts.
- Gate is 0.52. Nothing passes, so `production` and every `forecast` are `null`. The Dashboard
  shows "No forecast" and the Model performance page shows "No production model".
- Forecast log: 183 rows, 180 resolved, 91 hits (0.506), 3 pending.

## Problems to fix (DS/ML lane)

1. **Reddit is missing for all three stocks.** The code is merged, and `ml/ingest/reddit.py`
   omits the source on HTTP 403 or 429, so the most likely cause is Reddit refusing the
   request. This has not been confirmed. Run the pipeline and read the `reddit ... HTTP ...;
   omitting reddit` log lines. If Reddit keeps refusing, leave the source out and say so in
   the methodology note. Do not publish a made-up score.
2. **A gap summary contradicts the labels.** NVDA reads "Wall Street analysts lean bullish
   while News media lean bearish", but news is +15, labelled `neutral`. Build the sentence
   from each source's actual `label`: only say "bearish" for a `bearish` label, and use
   wording such as "while News media are neutral" otherwise. Add a test in
   `ml/tests/test_gap.py` for a bullish-against-neutral pair.
3. **Versions 4 and 5 are identical.** Both are `direction-xgb` at 0.4955, trained eight
   minutes apart. Each pipeline run appends a version even when nothing changed, so the
   registry fills with duplicates. Skip the append when the algorithm, parameters and data
   end date match the latest version, or give the pipeline a flag that publishes without
   retraining. Do not rewrite or delete the existing five rows without both humans agreeing.
4. **Versions 1 to 3 still carry unrounded accuracy** (`0.4895833333333333`). Cosmetic. The
   UI formats them. Leave them unless you are already touching the history.

## What to do next, in order

| # | Ticket | Notes |
|---|---|---|
| 1 | Problems 1 to 3 above | Small. Problem 2 is user-visible on the Dashboard right now. |
| 2 | [F2-ML-1](https://github.com/aisha-sk/stock-wiki/issues/15): MLflow tracking | Mostly in place (`ml/tracking.py`, run IDs on versions 2 to 5). Check each acceptance criterion: params, metrics, the four artifacts, a logged model, and the `docs/img/mlflow.png` screenshot. Then close it. |
| 3 | [F2-ML-2](https://github.com/aisha-sk/stock-wiki/issues/16): gate and registry | Statuses and `gate_passed` are published. Check the promotion rule, the append-only history (see problem 3) and the tests the issue lists. Then close it. |
| 4 | [F2-ML-3](https://github.com/aisha-sk/stock-wiki/issues/17) | Code is merged. Confirm its acceptance criteria and close it. |
| 5 | [F2-INT](https://github.com/aisha-sk/stock-wiki/issues/19): Checkpoint 2 | With @aisha-sk, once 1 to 4 are done. |

Then Flow 3 for DS/ML: [F3-ML-2](https://github.com/aisha-sk/stock-wiki/issues/24)
(methodology write-up, keep) before [F3-ML-1](https://github.com/aisha-sk/stock-wiki/issues/23)
(scheduled retraining, stretch).

Read each issue in full before starting: `gh issue view <number>`.

Open decision for the humans, unchanged: keep the "No forecast" result, or spend a time-boxed
hour trying to improve the model. Either way the gate stays at 0.52.

## What the SWE side does next

F3-SWE-1 (Alerts page, `POST /api/alerts`, `GET /api/alerts/preview`), then F3-SWE-2 (deploy).
The alert preview reads `sentiment.sources[].previous_score`, which the artifacts now carry.
None of it changes the contract or touches `ml/` or `data/artifacts/`.

## How to ship a ticket

1. `git checkout main && git pull`
2. `git checkout -b ml/<ticket-id>-short-name`
3. Do the work. Stay inside `ml/` and `data/artifacts/`.
4. Run the pipeline, then `python scripts/validate_contracts.py data/artifacts`, then
   `pytest ml -m "not slow"` and `ruff check ml`.
5. Open a PR **into `main`**, with `Closes #<issue number>` in the body. An issue only closes
   automatically when its PR merges straight into `main`.
6. Wait for CI to go green, then merge with **Create a merge commit** before starting the
   next ticket.

Do not stack PRs on each other. PRs #41 and #43 did this correctly.

## Things that must not change without both people agreeing

- Anything in `contracts/` or `docs/CONTRACT.md`: field names, units, enums.
- The gate threshold (0.52).
- Files in `api/`, `web/` and `.github/workflows/ci.yml`.
- No "buy" or "sell" wording in `gap.summary` or anywhere else.

## Earlier history

Kickoff fixed the contract, plan and 27 tickets. Flow 1 delivered the API, the Dashboard, price
ingestion, the walk-forward model, FinBERT news scoring and the publisher. Checkpoint 1 passed
on real data for TSLA, NVDA and AAPL; the results are on issue #10, which is still open and
can be closed.
