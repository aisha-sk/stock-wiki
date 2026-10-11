"""Answers "why do these groups disagree about this stock?" from StockSense's own data.

Claude reads the published sentiment and headlines through tools, then submits a short
answer in which every claim points at a headline. An answer that cites a headline we did not
publish is rejected, so the reply can always be checked against the dashboard.
"""

import json
import os
from datetime import UTC, datetime
from typing import Any

import anthropic

from . import tools

DEFAULT_MODEL = "claude-opus-5-5"
MAX_TURNS = 6
MAX_REJECTED_ANSWERS = 2

SYSTEM = """You explain to a general reader why different groups feel differently about one stock.

You are part of StockSense, a site that shows how Wall Street analysts, news media and Reddit each \
read a stock on a scale from -100 (bearish) to 100 (bullish). The reader has just looked at \
those scores and asked a question about them.

Use the tools to look up the scores and the headlines behind them before you answer. The tools \
are the only source you have: the reader can check every headline on the page, so anything you \
say that is not in a tool result would be unverifiable and must be left out. That includes \
prices, dates, events and reasons you may recall from elsewhere.

Then call submit_answer once. Write three to five plain sentences. Say what each group is \
reacting to, and name the headlines that show it by listing their ids in `citations`. When the \
analysts' score has method "ratings", it comes from buy/hold/sell counts and not from text, so \
describe it as a ratings consensus. If the headlines do not explain the gap, say that plainly \
instead of guessing: an honest "the data does not show why" is a good answer.

StockSense is for research and education, so describe what people are saying and never what the \
reader should do. Do not recommend buying, selling or holding, and do not predict the price."""

READ_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_sentiment",
        "description": (
            "Each group's sentiment score for this stock (-100 bearish to 100 bullish), the score "
            "in the previous window, how many documents it is based on, and the gap between groups."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_headlines",
        "description": (
            "Recent scored headlines for this stock, newest first. Each has an `id` to cite it by, "
            "its group (`source`), publisher, title, score and label."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["analysts", "news", "reddit"],
                    "description": "Only this group's headlines. Omit for all groups.",
                },
                "limit": {"type": "integer", "description": "How many to return, 1 to 30. Default 10."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_forecast",
        "description": "The model's 5-day large-move forecast for this stock, or why there is none.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

SUBMIT_TOOL: dict[str, Any] = {
    "name": "submit_answer",
    "description": "Give the final answer. Call this exactly once, after looking up the data.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string", "description": "Three to five plain sentences."},
            "citations": {
                "type": "array",
                "items": {"type": "string"},
                "description": "The `id` of every headline the answer relies on. At least one.",
            },
        },
        "required": ["answer", "citations"],
        "additionalProperties": False,
    },
}


class ExplainFailed(Exception):
    """The model did not produce an answer we can stand behind."""


def _run_read_tool(name: str, arguments: dict[str, Any], symbol: str) -> Any:
    # Tools are bound to the stock the reader asked about; the model cannot look elsewhere.
    if name == "get_sentiment":
        return tools.get_sentiment(symbol)
    if name == "get_headlines":
        return tools.get_headlines(symbol, arguments.get("source"), arguments.get("limit", 10))
    if name == "get_forecast":
        return tools.get_forecast(symbol)
    raise tools.LookupFailed(f"Unknown tool: {name}")


def _check_answer(arguments: dict[str, Any], known: dict[str, dict[str, Any]]) -> str | None:
    """Return what is wrong with a submitted answer, or None if it can be published."""
    if not str(arguments.get("answer", "")).strip():
        return "The answer is empty."
    cited = arguments.get("citations") or []
    if not cited:
        return "Cite at least one headline id from get_headlines."
    unknown = [c for c in cited if c not in known]
    if unknown:
        return (
            f"These ids are not headlines for this stock: {', '.join(unknown)}. Use ids from get_headlines."
        )
    return None


def explain(symbol: str, question: str, client: anthropic.Anthropic | None = None) -> dict[str, Any]:
    """Answer `question` about `symbol`. Raises ExplainFailed or an anthropic error."""
    known = {h["id"]: h for h in tools.get_headlines(symbol, limit=30)}
    symbol = tools.get_sentiment(symbol)["symbol"]
    client = client or anthropic.Anthropic()
    model = os.environ.get("EXPLAIN_MODEL") or DEFAULT_MODEL

    messages: list[dict[str, Any]] = [{"role": "user", "content": f"Stock: {symbol}\nQuestion: {question}"}]
    rejected = 0

    for _ in range(MAX_TURNS):
        response = client.beta.messages.create(
            model=model,
            max_tokens=4000,
            system=SYSTEM,
            tools=[*READ_TOOLS, SUBMIT_TOOL],
            output_config={"effort": "low"},
            # If a safety classifier declines, the API retries on a fallback model in the same call.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=messages,
        )
        if response.stop_reason == "refusal":
            raise ExplainFailed("The model declined to answer.")
        if response.stop_reason == "max_tokens":
            raise ExplainFailed("The answer was cut off.")

        messages.append({"role": "assistant", "content": response.content})
        calls = [block for block in response.content if block.type == "tool_use"]
        if not calls:
            messages.append({"role": "user", "content": "Call submit_answer with your answer and citations."})
            continue

        # Every tool call in the turn gets a result, all in one user message.
        results: list[dict[str, Any]] = []
        accepted: dict[str, Any] | None = None
        for call in calls:
            arguments = call.input if isinstance(call.input, dict) else {}
            if call.name == "submit_answer":
                problem = _check_answer(arguments, known)
                if problem is None and accepted is None:
                    accepted = arguments
                    content, is_error = "Accepted.", False
                else:
                    rejected += 1
                    content, is_error = problem or "Only one answer can be submitted.", True
            else:
                try:
                    content, is_error = json.dumps(_run_read_tool(call.name, arguments, symbol)), False
                except tools.LookupFailed as exc:
                    content, is_error = str(exc), True
            results.append(
                {"type": "tool_result", "tool_use_id": call.id, "content": content, "is_error": is_error}
            )

        if accepted is not None:
            cited = list(dict.fromkeys(accepted["citations"]))
            return {
                "symbol": symbol,
                "answer": accepted["answer"].strip(),
                "citations": [
                    {"headline_id": c, "title": known[c]["title"], "url": known[c]["url"]} for c in cited
                ],
                "model": response.model,
                "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        if rejected >= MAX_REJECTED_ANSWERS:
            raise ExplainFailed("The model could not support its answer with our headlines.")
        messages.append({"role": "user", "content": results})

    raise ExplainFailed("The model did not reach an answer.")
