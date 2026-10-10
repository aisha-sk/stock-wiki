# 24-hour plan

**Start:** Fri Oct 9, 2026, 9:40 pm Edmonton (11:40 pm Toronto).
**Hard stop:** Sat Oct 10, 9:40 pm Edmonton (11:40 pm Toronto).

Two people, two lanes:

| Lane | Owns | Folders |
|---|---|---|
| **SWE** (@aisha-sk, Edmonton) | Web app, API, CI, deploy | `web/`, `api/`, `.github/` |
| **DS/ML** (@SubaitaM, Toronto) | Data, sentiment, forecasting model, MLflow, gate | `ml/`, `data/artifacts/` |
| Shared | The contract | `contracts/`, `docs/`, `scripts/` |
| Stretch | Agent and MCP server | `agent/` |

The lanes meet at exactly one place: the JSON files described in [CONTRACT.md](CONTRACT.md).
SWE builds against the fake fixtures in `contracts/examples` from the first minute. DS/ML
replaces them with real files in `data/artifacts`. Nobody waits on anybody.

## The three flows

Each flow ends with a demo that works. Do not start a flow until the previous checkpoint passes.
Ticket IDs link to their GitHub issues, which hold the full task lists and acceptance criteria.
Board: https://github.com/users/aisha-sk/projects/2

### Flow 1: Working MVP (must finish)

**Done when:** you open the site, Tesla is selected, and the price chart, forecast, sentiment
and headlines on screen all come from files the ML pipeline wrote, served through the API.

| ID | Lane | Ticket | Est. |
|---|---|---|---|
| [F0-1](https://github.com/aisha-sk/stock-wiki/issues/1) | Both | Kickoff: clone, read the contract, run the validator, confirm roles and keys | 0.5 h |
| [F1-SWE-2](https://github.com/aisha-sk/stock-wiki/issues/2) | SWE | FastAPI: `/api/health`, `/api/tickers`, `/api/stocks/{symbol}` from `DATA_DIR` | 1 h |
| [F1-SWE-1](https://github.com/aisha-sk/stock-wiki/issues/3) | SWE | Next.js shell: tabs, stock selector, design tokens, typed API client | 1 h |
| [F1-SWE-3](https://github.com/aisha-sk/stock-wiki/issues/4) | SWE | Dashboard: quote header, price chart, forecast card | 1.5 h |
| [F1-SWE-4](https://github.com/aisha-sk/stock-wiki/issues/5) | SWE | Dashboard: sentiment spectrum, perspective gap, headlines | 1.5 h |
| [F1-ML-1](https://github.com/aisha-sk/stock-wiki/issues/6) | DS/ML | ML scaffold and daily price ingestion | 0.75 h |
| [F1-ML-2](https://github.com/aisha-sk/stock-wiki/issues/7) | DS/ML | Features, target, walk-forward logistic regression, metrics and baselines | 1.75 h |
| [F1-ML-3](https://github.com/aisha-sk/stock-wiki/issues/8) | DS/ML | News ingestion and FinBERT scoring | 1.5 h |
| [F1-ML-4](https://github.com/aisha-sk/stock-wiki/issues/9) | DS/ML | Publisher: write and validate the four artifact files for TSLA | 1 h |
| [F1-INT](https://github.com/aisha-sk/stock-wiki/issues/10) | Both | Checkpoint 1: flip `DATA_DIR` to real data, walk the dashboard together | 0.5 h |

### Flow 2: Connected AI and MLOps (the portfolio core)

**Done when:** the Model performance tab shows real out-of-sample metrics beside their
baselines, a registry with each version's gate result, and a Hit/Miss log, for three tickers,
and CI is green.

| ID | Lane | Ticket | Est. |
|---|---|---|---|
| [F2-SWE-1](https://github.com/aisha-sk/stock-wiki/issues/11) | SWE | API: `/api/model`, `/api/forecasts`, endpoint tests | 1 h |
| [F2-SWE-2](https://github.com/aisha-sk/stock-wiki/issues/12) | SWE | Model performance page: metric cards, weekly chart, registry, forecast log | 1.5 h |
| [F2-SWE-3](https://github.com/aisha-sk/stock-wiki/issues/13) | SWE | Loading, error, empty and `null` states; demo badge; disclaimer | 1 h |
| [F2-SWE-4](https://github.com/aisha-sk/stock-wiki/issues/14) | SWE | CI: lint, type check, tests, contract validation | 0.75 h |
| [F2-ML-1](https://github.com/aisha-sk/stock-wiki/issues/15) | DS/ML | MLflow tracking for every training run | 0.75 h |
| [F2-ML-2](https://github.com/aisha-sk/stock-wiki/issues/16) | DS/ML | Quality gate and registry, exported to `model.json` | 1 h |
| [F2-ML-3](https://github.com/aisha-sk/stock-wiki/issues/17) | DS/ML | XGBoost candidate, three tickers, backtest log, weekly accuracy, Sharpe, drawdown | 1.5 h |
| [F2-ML-4](https://github.com/aisha-sk/stock-wiki/issues/18) | DS/ML | Reddit and analyst sources, three-way spectrum, `previous_score` | 1.5 h |
| [F2-INT](https://github.com/aisha-sk/stock-wiki/issues/19) | Both | Checkpoint 2: three tickers end to end on real data | 0.5 h |

### Flow 3: Product polish and automation (stretch, cut from the bottom)

**Done when:** there is a public URL, the Alerts tab stores a sign-up, and the README tells the story.

| ID | Lane | Ticket | Est. | Cut order |
|---|---|---|---|---|
| [F3-SWE-1](https://github.com/aisha-sk/stock-wiki/issues/20) | SWE | Alerts: `POST /api/alerts`, preview endpoint, Alerts page | 1.5 h | keep |
| [F3-SWE-2](https://github.com/aisha-sk/stock-wiki/issues/21) | SWE | Deploy web and API, live link in README | 1 h | keep |
| [F3-ML-2](https://github.com/aisha-sk/stock-wiki/issues/24) | DS/ML | Methodology and limitations write-up | 0.75 h | keep |
| [F3-INT](https://github.com/aisha-sk/stock-wiki/issues/27) | Both | Final: demo script, README, production smoke test | 1 h | keep |
| [F3-SWE-3](https://github.com/aisha-sk/stock-wiki/issues/22) | SWE | Polish: responsive, accessibility, methodology section in the UI | 1 h | cut 4th |
| [F3-ML-1](https://github.com/aisha-sk/stock-wiki/issues/23) | DS/ML | Scheduled retraining workflow, live forecast logging and resolver | 1.5 h | cut 3rd |
| [F3-AG-1](https://github.com/aisha-sk/stock-wiki/issues/25) | Agent | MCP server over our own data | 1.5 h | cut 2nd |
| [F3-AG-2](https://github.com/aisha-sk/stock-wiki/issues/26) | Agent | "Explain this gap" agent with citations, plus UI panel | 1.5 h | cut 1st |

## Schedule

Working time is about 16 hours inside the 24. The sleep block is a suggestion; the checkpoints are not.

| Edmonton (MT) | Toronto (ET) | What |
|---|---|---|
| Fri 9:40 pm | Fri 11:40 pm | F0-1 kickoff on a call. Both run the validator and see it pass. |
| Fri 10:10 pm | Sat 12:10 am | Start F1-SWE-1 and F1-ML-1. Push something before bed. |
| Fri 11:30 pm | Sat 1:30 am | Sleep. Whoever is up first keeps going alone; the fixtures make that safe. |
| Sat 8:00 am | Sat 10:00 am | Both online. Rest of Flow 1. |
| **Sat 12:00 pm** | **Sat 2:00 pm** | **Checkpoint 1.** Flow 1 demo works on real TSLA data. |
| Sat 12:30 pm | Sat 2:30 pm | Flow 2. |
| **Sat 4:30 pm** | **Sat 6:30 pm** | **Checkpoint 2.** Three tickers, Model performance tab, CI green. |
| Sat 5:00 pm | Sat 7:00 pm | Flow 3, in keep order. |
| **Sat 8:00 pm** | **Sat 10:00 pm** | **Feature freeze.** Nothing new after this. |
| Sat 8:00 pm | Sat 10:00 pm | F3-INT: smoke test, README, demo run-through. |
| Sat 9:40 pm | Sat 11:40 pm | Done. |

**If Checkpoint 1 slips past 1:30 pm MT:** skip F2-ML-4 (Reddit and analysts) and ship a
news-only spectrum. The UI already handles one source.
**If Checkpoint 2 slips past 6:00 pm MT:** Flow 3 becomes F3-SWE-2 (deploy), F3-ML-2
(methodology) and F3-INT only.

## Decisions already made

These are settled so nobody burns an hour on them. Change one only by telling the other person.

| Topic | Decision | Why |
|---|---|---|
| Name | Product is "SentiFi" in the UI. Repo is `stock-wiki`. | Matches the mock. |
| Tickers | TSLA first, then NVDA and AAPL | Matches the mock. One high-drama name, two calmer ones. |
| Web | Next.js (App Router, TypeScript), Tailwind, Recharts | Fast to build, deploys to Vercel in minutes. |
| API | FastAPI, Pydantic v2, thin file-serving layer | Python on both sides of the artifact files. |
| Storage | JSON artifacts in git, SQLite for alert sign-ups | No database setup tonight. Supabase is a post-MVP move. |
| Prices | `yfinance`, daily closes, 2 years of history | Free, no key. |
| News | `yfinance` news first; Finnhub company news if a key exists | Free. |
| Reddit | Public subreddit search RSS with a custom User-Agent | The official API needs approval we will not get in a day. |
| Analysts | Finnhub recommendation trends, or `yfinance` recommendations | Ratings counts are free. Analyst report text is paywalled. Scored by `method: "ratings"`. |
| Sentiment model | FinBERT (`ProsusAI/finbert`), local | Free, finance-specific, no API key. |
| Forecast target | Close in 5 trading days above today's close | From the plan. |
| Forecast models | Logistic regression in Flow 1, XGBoost as a candidate in Flow 2 | Baseline first, so there is always something to ship. |
| Validation | Walk-forward only, never a random split | Random splits leak the future. |
| Baselines | `always_up`, `previous_direction`, shown beside the model | A model that cannot beat them should say so. |
| Quality gate | `directional_accuracy >= threshold`. Threshold is agreed at kickoff, before any result is seen (suggested 0.52), lives in `ml/config.yaml` and is published in `model.json` | The UI reads the threshold; nothing is hardcoded. Fixing it up front means it cannot be tuned to make a model pass. |
| If no model passes | `production` and `forecast` are `null` and the UI says so | An honest empty state beats a forecast from a model that failed its own test. |
| Registry history | Carried in `model.json` `versions`; each pipeline run reads the old list and appends | It survives CI runs, where the local MLflow store does not. |
| Track record on day one | Hit/Miss rows are `origin: "backtest"`; today's forecasts are `origin: "live"`, `pending` | Live forecasts need 5 trading days to resolve. |
| MLflow | Local file store in `mlruns/` (gitignored). Registry summary is exported into `model.json` | The web app never needs a running MLflow server. |
| Alerts | Stored, not emailed (`delivery: "mock"`) | Real email is a post-MVP item. |
| Agent | Stretch. It answers "why do these sources disagree?" with citations over our own data. Ingestion and scoring stay plain scripts. | Scripts are more reliable for pipelines; the agent gets the part that needs reasoning. |
| Out of scope | Kafka, user accounts and passwords, real email, deep learning models, more than 3 tickers | Not in 24 hours. |

## Rules that keep the result honest

- The forecast and the sentiment are separate things. Sentiment describes what people are
  saying. The forecast is a model's estimate of direction. Neither is advice.
- Report the accuracy you measure. Five-day direction is close to a coin flip, and a number
  near 50% next to its baselines is a legitimate result.
- No "buy" or "sell" wording anywhere, in the UI, the alert text or the agent's answers.
- Every page carries the disclaimer: research and education only, not financial advice.
- Anything fake is labelled. `is_demo_data: true` puts a "Demo data" badge on the page.

## After the 24 hours

Supabase Postgres in place of JSON files, hand-labelled headlines to compare FinBERT against
an LLM scorer, the ablation study (price features alone against price plus sentiment), real
email delivery, and more tickers.
