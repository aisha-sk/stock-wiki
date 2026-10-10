# ground-news-for-stocks:

A weather app for how people feel about a stock. Pick a ticker and see how Wall Street
analysts, news media and Reddit each read it, how far apart they are, and a model's 5-day
direction forecast with its track record in the open, misses included.

> Research and education only. Nothing here is financial advice, and past forecasts do not
> guarantee future results.

**Status:** 24-hour build in progress. The contract and plan are settled; the app is being built.

## The three tabs

| Tab | Question it answers |
|---|---|
| Dashboard | What is going on with this stock right now? Price, forecast, sentiment spectrum, headlines. |
| Model performance | Can I trust the forecasts? Accuracy against baselines, the version registry, a Hit/Miss log. |
| Alerts | Tell me when the story changes. Sign up for an email when sentiment shifts. |

## How it fits together

```
ml/  ──▶  data/artifacts/*.json  ──▶  api/ (FastAPI)  ──▶  web/ (Next.js)
```

The ML pipeline writes four kinds of JSON file. The API serves them. The web app renders them.
The file shapes are fixed in [docs/CONTRACT.md](docs/CONTRACT.md), and `contracts/examples`
holds fake versions so each side can be built without the other.

## Repo layout

| Path | What | Owner |
|---|---|---|
| `web/` | Next.js dashboard | SWE |
| `api/` | FastAPI service | SWE |
| `ml/` | Ingestion, sentiment scoring, forecasting model, MLflow, quality gate | DS/ML |
| `data/artifacts/` | Real pipeline output, served by the API | DS/ML |
| `agent/` | Stretch: MCP server and the "explain this gap" agent | Agent |
| `contracts/` | JSON Schemas and example payloads | Shared |
| `scripts/validate_contracts.py` | Checks any data directory against the contract | Shared |
| `design/` | The original UI mock | Reference |
| `docs/` | [Contract](docs/CONTRACT.md), [plan](docs/PLAN.md) | Shared |

## Start here

```bash
git clone git@github.com:aisha-sk/stock-wiki.git
```

```bash
pip install "jsonschema[format]"
```

```bash
python scripts/validate_contracts.py
```

That last command should print `OK`. Then read [docs/PLAN.md](docs/PLAN.md) for your tickets
and [docs/CONTRACT.md](docs/CONTRACT.md) for the data shapes. If you work with an AI coding
agent, it reads [AGENTS.md](AGENTS.md).
