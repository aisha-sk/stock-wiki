import json
from types import SimpleNamespace

import pytest
from agent import tools
from agent.explain import ExplainFailed, explain


@pytest.fixture(autouse=True)
def fixtures(monkeypatch):
    monkeypatch.setenv("DATA_DIR", "contracts/examples")
    monkeypatch.delenv("EXPLAIN_MODEL", raising=False)


def call(name: str, arguments: dict, call_id: str = "c1") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=call_id, name=name, input=arguments)


def turn(*blocks, stop_reason="tool_use") -> SimpleNamespace:
    return SimpleNamespace(stop_reason=stop_reason, content=list(blocks), model="claude-test")


class FakeClient:
    """Stands in for anthropic.Anthropic: replays scripted turns and records each request."""

    def __init__(self, *turns):
        self.turns = list(turns)
        self.requests: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **request):
        # Snapshot, because the agent keeps appending to the same messages list.
        self.requests.append({**request, "messages": list(request["messages"])})
        return self.turns.pop(0)


def headline_ids(symbol: str, source: str) -> list[str]:
    return [h["id"] for h in tools.get_headlines(symbol, source=source)]


def test_looks_up_data_then_returns_a_cited_answer():
    analyst, reddit = headline_ids("TSLA", "analysts")[0], headline_ids("TSLA", "reddit")[0]
    client = FakeClient(
        turn(call("get_sentiment", {}, "a"), call("get_headlines", {"limit": 30}, "b")),
        turn(
            call("submit_answer", {"answer": " Analysts and Reddit differ. ", "citations": [analyst, reddit]})
        ),
    )
    result = explain("tsla", "Why do they disagree?", client=client)

    assert result["symbol"] == "TSLA"
    assert result["answer"] == "Analysts and Reddit differ."
    assert [c["headline_id"] for c in result["citations"]] == [analyst, reddit]
    assert all(c["title"] for c in result["citations"])
    assert result["model"] == "claude-test"

    first, second = client.requests
    assert first["model"] == "claude-opus-5-5"
    assert first["messages"] == [{"role": "user", "content": "Stock: TSLA\nQuestion: Why do they disagree?"}]
    # Both tool calls were answered in one user message, with real data.
    results = second["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    assert json.loads(results[0]["content"])["gap"]["points"] == 79
    assert len(json.loads(results[1]["content"])) == len(tools.get_headlines("TSLA", limit=30))


def test_tools_are_bound_to_the_requested_stock():
    nvda = headline_ids("NVDA", "news")[0]
    client = FakeClient(
        turn(call("get_headlines", {"source": "news"})),
        turn(call("submit_answer", {"answer": "News cooled.", "citations": [nvda]})),
    )
    explain("NVDA", "Why?", client=client)
    served = json.loads(client.requests[1]["messages"][-1]["content"][0]["content"])
    assert {h["id"] for h in served} == set(headline_ids("NVDA", "news"))


def test_an_invented_citation_is_sent_back_then_accepted_when_fixed():
    real = headline_ids("TSLA", "news")[0]
    client = FakeClient(
        turn(call("submit_answer", {"answer": "Because.", "citations": ["made-up-id"]})),
        turn(call("submit_answer", {"answer": "Because of this.", "citations": [real]})),
    )
    result = explain("TSLA", "Why?", client=client)
    assert [c["headline_id"] for c in result["citations"]] == [real]
    rejection = client.requests[1]["messages"][-1]["content"][0]
    assert rejection["is_error"] and "made-up-id" in rejection["content"]


def test_headlines_from_another_stock_cannot_be_cited():
    other = headline_ids("NVDA", "news")[0]
    client = FakeClient(
        turn(call("submit_answer", {"answer": "Because.", "citations": [other]})),
        turn(call("submit_answer", {"answer": "Because.", "citations": [other]})),
    )
    with pytest.raises(ExplainFailed, match="could not support"):
        explain("TSLA", "Why?", client=client)


def test_an_answer_with_no_citations_is_never_returned():
    client = FakeClient(
        turn(call("submit_answer", {"answer": "Because.", "citations": []})),
        turn(call("submit_answer", {"answer": "Because.", "citations": []})),
    )
    with pytest.raises(ExplainFailed):
        explain("TSLA", "Why?", client=client)


def test_plain_text_without_a_tool_call_is_asked_to_submit():
    real = headline_ids("TSLA", "news")[0]
    client = FakeClient(
        turn(SimpleNamespace(type="text", text="Here is my answer."), stop_reason="end_turn"),
        turn(call("submit_answer", {"answer": "Fine.", "citations": [real]})),
    )
    assert explain("TSLA", "Why?", client=client)["answer"] == "Fine."
    assert "submit_answer" in client.requests[1]["messages"][-1]["content"]


def test_a_refusal_fails():
    with pytest.raises(ExplainFailed, match="declined"):
        explain("TSLA", "Why?", client=FakeClient(turn(stop_reason="refusal")))


def test_it_gives_up_after_too_many_turns():
    client = FakeClient(*[turn(call("get_sentiment", {})) for _ in range(6)])
    with pytest.raises(ExplainFailed, match="did not reach"):
        explain("TSLA", "Why?", client=client)


def test_an_unknown_symbol_fails_before_any_model_call():
    client = FakeClient()
    with pytest.raises(tools.LookupFailed):
        explain("XYZ", "Why?", client=client)
    assert client.requests == []
