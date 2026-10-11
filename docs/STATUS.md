# Status: Flow 3 SWE work merged, deploy and methodology remaining

Updated Sat Oct 10, 2026, 6:30 pm Edmonton, for SubaitaM's AI agent (DS/ML lane). Feature
freeze is 8:00 pm Edmonton (10:00 pm Toronto). For the rules of the repo read `AGENTS.md`, and
for every JSON shape read `docs/CONTRACT.md`. This file does not repeat them.

## Do this first

```bash
git checkout main
git pull
python scripts/validate_contracts.py data/artifacts
```

The last command must print `OK ... (3 ticker(s))`. `main` is at `6d57a76` plus this file, and
CI is green. Start every new ticket from a fresh branch off `main`.

## What changed since the last status

All of it is on `main`.

| What | PR | What it means for DS/ML |
|---|---|---|
| Fonts bundled in the app | #47 | Nothing. |
| Alerts: `POST /api/alerts`, `GET /api/alerts/preview`, Alerts page | #48 | The example email reads `sentiment.sources[].previous_score`. Keep publishing it. |
| Landing page at `/`; the dashboard moved to `/dashboard` | #49 | The landing page shows the stock with the widest `gap.points`, and a scorecard built from `model.json` and the forecast summary. |
| Dockerfile, Render blueprint, deploy guide | #50 | The API image contains `data/artifacts` as it is on `main` when built. New data goes live when merged to `main`. |
| MCP server and explain agent in `agent/` | #51 | New `Agent` CI job. See the contract note below. |
| README with results and screenshots; `docs/DEMO.md` | #52 | The README quotes numbers from the current artifacts. See "If you re-run the pipeline". |

Checkpoint 2 passed and is closed (#19). All Flow 2 tickets are closed.

## Contract note: please read

PR #51 edited `docs/CONTRACT.md` and was merged without your approval, on @aisha-sk's
instruction. The edit is to the optional `POST /api/explain` section only:

- the example `model` value is now `claude-opus-5-5`
- on a 503 the UI shows a note instead of hiding the panel

No schema, field, unit or enum changed, and nothing the pipeline produces is affected. If you
disagree with either line, say so and it will be changed back.

## What the app shows on the current artifacts

Artifacts generated `2026-10-10T22:13:54Z`. They pass the validator.

| Stock | Analysts | News | Reddit | Gap |
|---|---|---|---|---|
| TSLA | +19 | +22 | missing | 3 |
| NVDA | +55 | +15 | missing | 40 |
| AAPL | +25 | +8 | missing | 17 |

- Best version: `direction-xgb` v7 at 0.4955. Baselines: always-up 0.5253, previous-direction
  0.4747, over 672 test forecasts.
- Seven versions, none past the 0.52 gate. `production` and every `forecast` are `null`.
- Forecast log: 91 of 180 resolved correct (0.506), 3 pending.

## What is left for DS/ML, in order

| # | Ticket | Notes |
|---|---|---|
| 1 | [F3-ML-2](https://github.com/aisha-sk/stock-wiki/issues/24): `docs/METHODOLOGY.md` | Must finish. The README has a slot for the link. Every number in it must match `data/artifacts/model.json` on the same commit. |
| 2 | Reddit | Still missing for every stock, cause unconfirmed. Run the pipeline and read the `reddit ... HTTP ...; omitting reddit` log lines. If Reddit keeps refusing, leave it out and say so in the methodology. The README already says Reddit is not in the data. |
| 3 | Duplicate versions | Versions 4 to 7 are identical `direction-xgb` runs at 0.4955. Make the pipeline skip the append when nothing changed. Do not delete existing rows without both humans agreeing. |
| 4 | [F3-ML-1](https://github.com/aisha-sk/stock-wiki/issues/23): scheduled retraining | Stretch. Only if 1 is done and there is time before the freeze. |
| 5 | [F3-INT](https://github.com/aisha-sk/stock-wiki/issues/27): final | With @aisha-sk after the freeze. |

Open decision for the humans, unchanged: keep the "No forecast" result, or spend a time-boxed
hour on the model (more tickers and history, market-context features). The gate stays at 0.52
either way.

## If you re-run the pipeline

A new run changes numbers that are now quoted in three places. In the same PR, update:

- `README.md`, section "What we measured" (accuracy, baselines, version count, forecast log)
- `docs/DEMO.md` (the numbers in the "Say" column and the "If someone asks" table)
- `docs/METHODOLOGY.md`

Each full training run also appends a model version, so until item 3 above is fixed, re-run
only when the data or the model actually changed.

## CI on your PRs

Five jobs now run on every pull request: Contract validation, API, Web, ML, Agent. For DS/ML
the two that matter are unchanged:

- **Contract validation** runs `scripts/validate_contracts.py` on `data/artifacts`.
- **ML** runs `ruff check ml` and `pytest ml -m "not slow"` with a light package list. torch,
  transformers and mlflow are not installed, so tests that need them must be marked
  `@pytest.mark.slow` or skip when the import is missing.

## What the SWE side does next

Deploying: the API to Render and the web app to Vercel, following `docs/DEPLOY.md`. Then the
live link goes into the README and both people smoke-test the deployed site for F3-INT.

## How to ship a ticket

1. `git checkout main && git pull`
2. `git checkout -b ml/<ticket-id>-short-name`
3. Do the work. Stay inside `ml/`, `data/artifacts/` and `docs/METHODOLOGY.md`.
4. Run the pipeline if needed, then `python scripts/validate_contracts.py data/artifacts`,
   `pytest ml -m "not slow"` and `ruff check ml`.
5. Open a PR **into `main`** with `Closes #<issue number>` in the body.
6. Wait for CI to go green, then merge with **Create a merge commit**.

Do not stack PRs on each other.

## Things that must not change without both people agreeing

- Anything in `contracts/` or `docs/CONTRACT.md`: field names, units, enums.
- The gate threshold (0.52).
- Files in `api/`, `web/`, `agent/` and `.github/workflows/ci.yml`.
- No "buy" or "sell" wording in `gap.summary` or anywhere else.
