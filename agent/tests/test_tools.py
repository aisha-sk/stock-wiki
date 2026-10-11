import asyncio
import json
from pathlib import Path

import pytest
from agent import tools
from agent.mcp_server import server

EXAMPLES = Path(__file__).resolve().parents[2] / "contracts" / "examples"


@pytest.fixture(autouse=True)
def fixtures(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "contracts/examples")


def example(relative: str) -> dict:
    return json.loads((EXAMPLES / relative).read_text())


def test_list_tickers():
    assert [t["symbol"] for t in tools.list_tickers()] == ["TSLA", "NVDA", "AAPL"]


def test_get_sentiment_is_the_published_sentiment():
    stock = example("stocks/TSLA.json")
    result = tools.get_sentiment("tsla")
    assert result["sources"] == stock["sentiment"]["sources"]
    assert result["gap"] == stock["sentiment"]["gap"]


def test_get_headlines_filters_and_limits():
    stock = example("stocks/TSLA.json")
    assert tools.get_headlines("TSLA", limit=2) == stock["headlines"][:2]
    reddit = tools.get_headlines("TSLA", source="reddit")
    assert reddit and {h["source"] for h in reddit} == {"reddit"}


def test_get_headlines_rejects_an_unknown_source():
    with pytest.raises(tools.LookupFailed, match="source must be"):
        tools.get_headlines("TSLA", source="twitter")


def test_get_forecast():
    assert tools.get_forecast("NVDA")["forecast"] == example("stocks/NVDA.json")["forecast"]


def test_get_forecast_explains_a_missing_forecast(tmp_path, monkeypatch):
    for name in ("tickers.json",):
        (tmp_path / name).write_text((EXAMPLES / name).read_text())
    stock = example("stocks/TSLA.json")
    stock["forecast"] = None
    (tmp_path / "stocks").mkdir()
    (tmp_path / "stocks" / "TSLA.json").write_text(json.dumps(stock))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    result = tools.get_forecast("TSLA")
    assert result["forecast"] is None and "quality gate" in result["reason"]


def test_get_track_record_summary_matches_the_rows():
    everything = tools.get_track_record()
    assert everything["summary"] == example("forecasts.json")["summary"]
    tsla = tools.get_track_record("TSLA")
    assert {r["symbol"] for r in tsla["forecasts"]} == {"TSLA"}
    assert tsla["summary"] == {"resolved": 2, "hits": 1, "hit_rate": 0.5, "pending": 1}


def test_get_model_card():
    card = tools.get_model_card()
    model = example("model.json")
    assert card["metrics"] == model["metrics"] and card["versions"] == model["versions"]


def test_unknown_symbol_is_a_readable_error():
    with pytest.raises(tools.LookupFailed, match="Unknown symbol: XYZ. Tracked symbols: TSLA, NVDA, AAPL"):
        tools.get_sentiment("xyz")


def test_missing_data_is_a_readable_error(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    with pytest.raises(tools.LookupFailed, match="not available"):
        tools.list_tickers()


def test_mcp_server_lists_the_six_tools():
    listed = asyncio.run(server.list_tools())
    assert sorted(tool.name for tool in listed) == [
        "get_forecast",
        "get_headlines",
        "get_model_card",
        "get_sentiment",
        "get_track_record",
        "list_tickers",
    ]
    assert all(tool.description for tool in listed)


def test_mcp_tool_call_returns_data_and_readable_errors():
    from mcp.server.mcpserver.exceptions import ToolError

    async def run():
        ok = await server.call_tool("get_sentiment", {"symbol": "nvda"})
        with pytest.raises(ToolError, match="Unknown symbol: XYZ"):
            await server.call_tool("get_sentiment", {"symbol": "XYZ"})
        return ok

    assert "NVDA" in str(asyncio.run(run()))
