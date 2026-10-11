# Instructions for AI coding agents

Two people are building this in 24 hours, each with their own AI agent. This file is how the
agents stay compatible. Read it, then read `docs/CONTRACT.md` before writing any code that
produces or consumes JSON.

## What this project is

StockSense shows how three groups feel about a stock (Wall Street analysts, news media, Reddit),
how far apart they are, and a model's 5-day direction forecast with its public track record.
Three tabs: Dashboard, Model performance, Alerts.

```
ml/ ──▶ data/artifacts/*.json ──▶ api/ (FastAPI) ──▶ web/ (Next.js)
```

## Read these first

| File | What it settles |
|---|---|
| `docs/CONTRACT.md` | Every JSON shape, unit, enum, endpoint, port and env var |
| `contracts/schemas/` | The machine-checked version of the contract |
| `contracts/examples/` | Valid example payloads with fake numbers. Use them as test fixtures. |
| `docs/PLAN.md` | The three flows, ticket IDs, schedule, decisions already made |
| `design/Main.dc.html` | The visual mock: layout, copy, colors. Reference only, not runnable code. |

## Lanes: stay in yours

| Lane | May edit | Must not edit |
|---|---|---|
| SWE | `web/`, `api/`, `.github/` | `ml/`, `data/artifacts/` |
| DS/ML | `ml/`, `data/artifacts/`, `.github/workflows/train.yml` | `web/`, `api/` |
| Agent (stretch) | `agent/`, plus the one `/api/explain` route and one UI panel | everything else |
| Both, by agreement | `contracts/`, `docs/`, `scripts/`, root files | |

If the task you were given needs a change outside your lane, stop and tell your human. Do not
make the change.

## Rules

1. **Never invent a field, rename one, or change a unit.** If the contract lacks something you
   need, stop and tell your human. Contract changes follow section 4 of `docs/CONTRACT.md`.
2. **The web app hardcodes no numbers.** Every figure on screen comes from the API. This
   includes the gate threshold, model version, dates and ticker names.
3. **The API adds nothing to artifact payloads.** `GET` responses are the artifact files.
4. **Handle `null` and missing sources.** `forecast` can be `null`. `sentiment.sources` can
   have 0 to 3 items. `gap` can be `null`. Four `metrics` fields can be `null`.
5. **Run the validator** before pushing anything that touches `contracts/` or `data/artifacts/`:
   `python scripts/validate_contracts.py data/artifacts`
6. **No look-ahead.** In `ml/`, a feature for day *t* uses only data available at the close of
   day *t*. Validation is walk-forward. No random train/test splits. No fitting scalers on the
   full dataset.
7. **Report measured numbers only.** Never write a metric into an artifact that the code did
   not compute. Never tune the gate threshold to make a model pass.
8. **No secrets in git.** Keys go in `.env` (gitignored). Add new variable names to `.env.example`.
9. **No financial-advice wording.** Never "buy", "sell", "should", "will go up". Use "the model
   estimates", "sentiment is".
10. **Keep the "Demo data" badge honest.** It shows exactly when `is_demo_data` is `true`.

## Conventions

- JSON: `snake_case`, UTC timestamps with `Z`, dates `YYYY-MM-DD`, lowercase enums.
- Sentiment scores are integers from -100 to 100. Probabilities and rates are fractions from
  0 to 1. Keys ending in `_pct` are percent units.
- Python 3.11, formatted and linted with `ruff`. Type hints on public functions.
- TypeScript strict mode. No `any` for API data: types in `web/src/lib/types.ts` mirror the schemas.
- Tests: `pytest` for `api/` and `ml/`. Use `contracts/examples` as fixtures.

## Commands

```bash
# contract
pip install "jsonschema[format]"
python scripts/validate_contracts.py                 # fixtures
python scripts/validate_contracts.py data/artifacts  # real pipeline output

# api (port 8000)
cd api && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
DATA_DIR=data/artifacts uvicorn app.main:app --reload --port 8000   # real data
pytest && ruff check .

# web (port 3000)
cd web && npm install && npm run dev

# ml
pip install -r ml/requirements.txt
python -m ml.pipeline --tickers TSLA NVDA AAPL --out data/artifacts
mlflow ui --port 5001
```

Commands for `api/`, `web/` and `ml/` start working as their Flow 1 tickets land. Keep this
list current when you add one.

## Git workflow

- Branch from `main`: `swe/<ticket-id>-short-name`, `ml/<ticket-id>-short-name`,
  `agent/<ticket-id>-short-name`. Example: `swe/f1-swe-3-price-chart`.
- One ticket per PR. Put `Closes #<issue number>` in the PR body.
- Commit messages: `<ticket-id>: what changed`. Example: `F1-ML-2: walk-forward logistic regression`.
- CI (`.github/workflows/ci.yml`) runs on every PR: contract validation, API, web and ML jobs.
  The ML job installs a light dependency list written in the workflow; add to it there if a
  fast test needs a new package.
- You may merge your own PR when CI is green and it only touches your lane.
- A PR labelled `contract-change` needs the other person's approval.
- Pull `main` before starting each ticket. Rebase, do not merge `main` into your branch.
- Never force-push `main`. Never commit `.env`, `mlruns/`, `*.db`, model binaries or raw data.

## Design tokens (from the mock)

| Token | Value |
|---|---|
| Page background | `#F5F6F8` |
| Card background | `#FFFFFF` |
| Text | `#11151B` |
| Muted text | `#5B6472` |
| Border | `#E3E6EB` |
| Bullish, up, hit | `#1D4ED8` |
| Bearish, down, miss | `#C2410C` |
| Neutral | `#5B6472` |
| Forecast card | `#11151B` background, `#FFFFFF` text, `#C5CBD6` secondary text |
| Fonts | IBM Plex Sans for text, IBM Plex Mono for numbers |
| Cards | 12 px radius, 1 px border, 24 px padding, 24 px gaps, 1200 px max width |

Blue and orange are used on purpose in place of green and red, so the spectrum reads for
colour-blind viewers. Keep them.
