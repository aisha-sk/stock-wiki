import json
from pathlib import Path

import pytest
from conftest import example
from jsonschema import Draft202012Validator, FormatChecker
from test_api import assert_error

SCHEMAS = Path(__file__).resolve().parents[2] / "contracts" / "schemas"


def test_model_is_the_file(client):
    response = client.get("/api/model")
    assert response.status_code == 200
    assert response.json() == example("model.json")


def test_model_without_a_production_version_is_served(client, data_copy):
    path = data_copy / "model.json"
    model = json.loads(path.read_text())
    model["production"] = None
    model["gate"]["passed"] = False
    for key in ("sharpe_ratio", "max_drawdown", "inference_latency_ms", "cost_per_request_usd"):
        model["metrics"][key] = None
    for version in model["versions"]:
        version["status"] = "rejected"
    path.write_text(json.dumps(model))
    response = client.get("/api/model")
    assert response.status_code == 200
    assert response.json() == model


def test_forecasts_unfiltered_is_the_file(client):
    response = client.get("/api/forecasts")
    assert response.status_code == 200
    assert response.json() == example("forecasts.json")


def test_forecasts_filter_by_symbol_recomputes_the_summary(client):
    body = client.get("/api/forecasts?symbol=TSLA").json()
    assert {row["symbol"] for row in body["forecasts"]} == {"TSLA"}
    assert body["summary"] == {"resolved": 2, "hits": 1, "hit_rate": 0.5, "pending": 1}


def test_forecasts_symbol_is_case_insensitive(client):
    assert client.get("/api/forecasts?symbol=nvda").json() == client.get("/api/forecasts?symbol=NVDA").json()


def test_forecasts_limit_trims_rows_but_not_the_summary(client):
    full = example("forecasts.json")
    body = client.get("/api/forecasts?limit=2").json()
    assert body["forecasts"] == full["forecasts"][:2]
    assert body["summary"] == full["summary"]


def test_forecasts_summary_with_nothing_resolved(client, data_copy):
    path = data_copy / "forecasts.json"
    forecasts = json.loads(path.read_text())
    forecasts["forecasts"] = [row for row in forecasts["forecasts"] if row["status"] == "pending"]
    forecasts["summary"] = {"resolved": 0, "hits": 0, "hit_rate": None, "pending": 3}
    path.write_text(json.dumps(forecasts))
    assert client.get("/api/forecasts").json()["summary"]["hit_rate"] is None


def test_forecasts_unknown_symbol_is_404(client):
    assert_error(client.get("/api/forecasts?symbol=XYZ"), 404, "not_found")


@pytest.mark.parametrize("limit", ["0", "201", "abc"])
def test_forecasts_bad_limit_is_422(client, limit):
    assert_error(client.get(f"/api/forecasts?limit={limit}"), 422, "validation_error")


def test_missing_files_are_503(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert_error(client.get("/api/model"), 503, "data_unavailable")
    assert_error(client.get("/api/forecasts"), 503, "data_unavailable")


@pytest.mark.parametrize(
    ("route", "schema"),
    [
        ("/api/tickers", "tickers.schema.json"),
        ("/api/stocks/TSLA", "stock.schema.json"),
        ("/api/stocks/NVDA", "stock.schema.json"),
        ("/api/stocks/AAPL", "stock.schema.json"),
        ("/api/model", "model.schema.json"),
        ("/api/forecasts", "forecasts.schema.json"),
        ("/api/forecasts?symbol=AAPL&limit=1", "forecasts.schema.json"),
    ],
)
def test_every_get_route_matches_its_json_schema(client, route, schema):
    validator = Draft202012Validator(
        json.loads((SCHEMAS / schema).read_text()), format_checker=FormatChecker()
    )
    problems = [error.message for error in validator.iter_errors(client.get(route).json())]
    assert problems == []


def test_health_matches_its_json_schema(client):
    api_schema = json.loads((SCHEMAS / "api.schema.json").read_text())
    validator = Draft202012Validator(api_schema["$defs"]["health"], format_checker=FormatChecker())
    assert list(validator.iter_errors(client.get("/api/health").json())) == []
