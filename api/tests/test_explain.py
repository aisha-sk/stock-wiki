import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from test_api import assert_error

from app import explainer

API_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[2] / "contracts" / "schemas" / "api.schema.json").read_text()
)
ASK = {"symbol": "TSLA", "question": "Why do analysts and Reddit disagree?"}


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    explainer._cache.clear()
    explainer._recent_calls.clear()


@pytest.fixture
def agent(monkeypatch):
    """Pretend a credential is set and replace the model call with a canned answer."""
    calls = []

    def run(symbol, question):
        calls.append((symbol, question))
        return {
            "symbol": symbol,
            "answer": "Analysts point to deliveries; Reddit points to margins.",
            "citations": [{"headline_id": "abc123", "title": "A headline", "url": None}],
            "model": "claude-test",
            "generated_at": "2026-10-10T18:00:00Z",
        }

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setattr(explainer, "_run", run)
    return calls


def test_without_a_credential_it_is_503_and_nothing_is_called(client, monkeypatch):
    monkeypatch.setattr(explainer, "_run", lambda *_: pytest.fail("the agent must not run"))
    assert_error(client.post("/api/explain", json=ASK), 503, "data_unavailable")


def test_answer_matches_the_contract(client, agent):
    response = client.post("/api/explain", json={**ASK, "symbol": "tsla"})
    assert response.status_code == 200
    body = response.json()
    validator = Draft202012Validator(API_SCHEMA["$defs"]["explain_response"], format_checker=FormatChecker())
    assert [e.message for e in validator.iter_errors(body)] == []
    assert body["symbol"] == "TSLA"
    assert agent == [("TSLA", ASK["question"])]


def test_the_same_question_is_answered_from_the_cache(client, agent):
    first = client.post("/api/explain", json=ASK).json()
    again = client.post("/api/explain", json={**ASK, "question": ASK["question"].upper()}).json()
    assert again == first
    assert len(agent) == 1


def test_calls_are_limited_per_minute(client, agent):
    for n in range(explainer.MAX_CALLS_PER_MINUTE):
        assert client.post("/api/explain", json={**ASK, "question": f"Question {n}?"}).status_code == 200
    assert_error(client.post("/api/explain", json={**ASK, "question": "One more?"}), 503, "data_unavailable")
    assert len(agent) == explainer.MAX_CALLS_PER_MINUTE


def test_a_failing_agent_is_503_without_leaking_the_reason(client, agent, monkeypatch):
    def boom(*_):
        raise RuntimeError("secret detail sk-ant-xxxx")

    monkeypatch.setattr(explainer, "_run", boom)
    response = client.post("/api/explain", json=ASK)
    assert_error(response, 503, "data_unavailable")
    assert "secret" not in response.text


def test_unknown_symbol_is_404(client, agent):
    assert_error(client.post("/api/explain", json={**ASK, "symbol": "XYZ"}), 404, "not_found")
    assert agent == []


@pytest.mark.parametrize(
    "body", [{"symbol": "TSLA"}, {**ASK, "question": ""}, {**ASK, "question": "x" * 501}]
)
def test_invalid_request_is_422(client, agent, body):
    assert_error(client.post("/api/explain", json=body), 422, "validation_error")
