"""MCP server over SentiFi's own data: sentiment, headlines, forecasts and the track record.

    python -m agent.mcp_server            # stdio, reads DATA_DIR (default: the demo fixtures)

It is read-only and needs no API key. See agent/README.md for connecting a client.
"""

import functools
from collections.abc import Callable
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import tools

server = MCPServer(
    "sentifi",
    instructions=(
        "Read-only access to SentiFi: how analysts, news media and Reddit feel about a stock "
        "(scores from -100 bearish to 100 bullish), the headlines behind each score, the model's "
        "5-day large-move forecast and its public track record. Nothing here is financial advice."
    ),
)


def _readable_errors(tool: Callable[..., Any]) -> Callable[..., Any]:
    """Pass a lookup problem to the client as a message. Other exceptions stay masked by MCP."""

    @functools.wraps(tool)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return tool(*args, **kwargs)
        except tools.LookupFailed as exc:
            raise ToolError(str(exc)) from None

    return wrapper


for _tool in (
    tools.list_tickers,
    tools.get_sentiment,
    tools.get_headlines,
    tools.get_forecast,
    tools.get_track_record,
    tools.get_model_card,
):
    server.tool()(_readable_errors(_tool))


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
