# agent

Two things built on StockSense's own published data. Both are read-only.

| File | What it is | Needs a key |
|---|---|---|
| `tools.py` | Six lookups over the artifact files: tickers, sentiment, headlines, forecast, track record, model card | No |
| `mcp_server.py` | An MCP server exposing those six lookups to any MCP client | No |
| `explain.py` | An agent that answers "why do these groups disagree?" and must cite real headlines | Yes |

Nothing here computes a new number. A tool returns what the dashboard already shows, so an
answer can always be checked against the page.

## MCP server

```bash
pip install -r agent/requirements.txt
```

```bash
DATA_DIR=data/artifacts python -m agent.mcp_server
```

It speaks MCP over stdio. To use it from Claude Code, add this to `.mcp.json` in the repo root:

```json
{
  "mcpServers": {
    "stocksense": {
      "command": "python",
      "args": ["-m", "agent.mcp_server"],
      "env": { "DATA_DIR": "data/artifacts" }
    }
  }
}
```

Then ask, for example, "Using stocksense, why do analysts and the news disagree about NVDA?"

`DATA_DIR` defaults to `contracts/examples` (demo data), the same as the API.

## Explain agent

`explain(symbol, question)` gives Claude three lookups bound to that one stock and a
`submit_answer` tool. The answer is only returned if every headline id it cites exists in that
stock's published headlines. An invented or missing citation is sent back once to be fixed,
then the call fails.

The API serves it at `POST /api/explain` (see `docs/CONTRACT.md`). It needs `ANTHROPIC_API_KEY`
on the server. Without one the endpoint returns 503 and the dashboard panel says the explainer
is not set up. `EXPLAIN_MODEL` picks the model (default `claude-opus-5-5`).

Each call costs money. The API caches answers per stock, question and data timestamp, and
allows 10 model calls a minute.

## Tests

```bash
pytest agent
```

The model is replaced by a scripted fake, so the tests need no key and make no network calls.
