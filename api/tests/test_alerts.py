import json
import sqlite3
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from test_api import assert_error

API_SCHEMA = json.loads(
    (Path(__file__).resolve().parents[2] / "contracts" / "schemas" / "api.schema.json").read_text()
)
SIGN_UP = {"email": "reader@example.com", "symbol": "TSLA", "trigger": "sharp_shift"}


def matches(name: str, body: dict) -> list[str]:
    validator = Draft202012Validator(API_SCHEMA["$defs"][name], format_checker=FormatChecker())
    return [error.message for error in validator.iter_errors(body)]


def rows(tmp_path) -> list[tuple]:
    with sqlite3.connect(tmp_path / "alerts.db") as connection:
        return connection.execute("SELECT email, symbol, trigger FROM alerts").fetchall()


def test_create_alert(client, tmp_path):
    response = client.post("/api/alerts", json=SIGN_UP)
    assert response.status_code == 201
    body = response.json()
    assert matches("alert_response", body) == []
    assert {k: body[k] for k in SIGN_UP} == SIGN_UP
    assert body["delivery"] == "mock"
    assert rows(tmp_path) == [("reader@example.com", "TSLA", "sharp_shift")]


def test_same_sign_up_twice_returns_the_existing_row(client, tmp_path):
    first = client.post("/api/alerts", json=SIGN_UP)
    again = client.post("/api/alerts", json={**SIGN_UP, "email": " Reader@Example.com", "symbol": "tsla"})
    assert again.status_code == 200
    assert again.json() == first.json()
    assert len(rows(tmp_path)) == 1


def test_a_different_trigger_is_a_new_sign_up(client, tmp_path):
    client.post("/api/alerts", json=SIGN_UP)
    response = client.post("/api/alerts", json={**SIGN_UP, "trigger": "weekly_digest"})
    assert response.status_code == 201
    assert len(rows(tmp_path)) == 2


@pytest.mark.parametrize(
    "body",
    [
        {**SIGN_UP, "email": "not-an-email"},
        {**SIGN_UP, "trigger": "hourly"},
        {**SIGN_UP, "extra": 1},
        {"email": "reader@example.com"},
    ],
)
def test_invalid_sign_up_is_422_and_stores_nothing(client, tmp_path, body):
    assert_error(client.post("/api/alerts", json=body), 422, "validation_error")
    assert not (tmp_path / "alerts.db").exists()


def test_unknown_symbol_is_404(client):
    assert_error(client.post("/api/alerts", json={**SIGN_UP, "symbol": "XYZ"}), 404, "not_found")


def test_preview_quotes_the_stock_payload(client):
    response = client.get("/api/alerts/preview?symbol=tsla")
    assert response.status_code == 200
    body = response.json()
    assert matches("alert_preview", body) == []
    assert body == {
        "symbol": "TSLA",
        "subject": "TSLA sentiment gap: 79 points",
        "body_lines": [
            "Reddit sentiment moved from -12 to -37 over the last 7 days, "
            "while Wall Street analysts stayed at +42.",
            "Model forecast, next 5 trading days: Up, 64% confidence.",
        ],
        "is_demo_data": True,
    }


def test_preview_without_forecast_gap_or_history(client, data_copy):
    path = data_copy / "stocks" / "NVDA.json"
    stock = json.loads(path.read_text())
    stock["forecast"] = None
    stock["sentiment"]["gap"] = None
    stock["sentiment"]["sources"] = [{**stock["sentiment"]["sources"][1], "previous_score": None}]
    path.write_text(json.dumps(stock))
    body = client.get("/api/alerts/preview?symbol=NVDA").json()
    assert body["subject"] == "NVDA sentiment update"
    assert body["body_lines"] == ["There is no sentiment change to report for NVDA yet."]


def test_preview_with_one_moving_source_and_no_forecast(client, data_copy):
    path = data_copy / "stocks" / "NVDA.json"
    stock = json.loads(path.read_text())
    stock["forecast"] = None
    stock["sentiment"]["sources"] = stock["sentiment"]["sources"][2:]
    stock["sentiment"]["gap"] = None
    path.write_text(json.dumps(stock))
    body = client.get("/api/alerts/preview?symbol=NVDA").json()
    assert body["body_lines"] == ["Reddit sentiment moved from +31 to -22 over the last 7 days."]


def test_preview_unknown_symbol_is_404(client):
    assert_error(client.get("/api/alerts/preview?symbol=XYZ"), 404, "not_found")


def test_preview_needs_a_symbol(client):
    assert_error(client.get("/api/alerts/preview"), 422, "validation_error")
