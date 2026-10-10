import json
import os
import time

from conftest import example


def assert_error(response, status: int, code: str) -> None:
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code
    assert body["error"]["message"]


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api_version": "1.0",
        "data_generated_at": example("model.json")["generated_at"],
        "is_demo_data": True,
    }


def test_health_stays_up_without_data(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["data_generated_at"] is None


def test_tickers_is_the_file(client):
    response = client.get("/api/tickers")
    assert response.status_code == 200
    assert response.json() == example("tickers.json")


def test_stock_is_the_file(client):
    for symbol in ("TSLA", "NVDA", "AAPL"):
        response = client.get(f"/api/stocks/{symbol}")
        assert response.status_code == 200
        assert response.json() == example(f"stocks/{symbol}.json")


def test_stock_symbol_is_case_insensitive(client):
    assert client.get("/api/stocks/tsla").json() == client.get("/api/stocks/TSLA").json()


def test_unknown_symbol_is_404(client):
    assert_error(client.get("/api/stocks/XYZ"), 404, "not_found")


def test_unknown_route_uses_the_error_shape(client):
    assert_error(client.get("/api/nope"), 404, "not_found")


def test_missing_data_is_503(client, tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    assert_error(client.get("/api/tickers"), 503, "data_unavailable")
    assert_error(client.get("/api/stocks/TSLA"), 503, "data_unavailable")


def test_missing_stock_file_is_503(client, data_copy):
    (data_copy / "stocks" / "TSLA.json").unlink()
    assert_error(client.get("/api/stocks/TSLA"), 503, "data_unavailable")


def test_file_that_breaks_the_contract_is_503(client, data_copy):
    path = data_copy / "stocks" / "TSLA.json"
    stock = json.loads(path.read_text())
    stock["forecast"]["probUp"] = 0.6
    path.write_text(json.dumps(stock))
    response = client.get("/api/stocks/TSLA")
    assert_error(response, 503, "data_unavailable")
    assert "probUp" not in response.text


def test_wrong_unit_is_rejected(client, data_copy):
    path = data_copy / "stocks" / "TSLA.json"
    stock = json.loads(path.read_text())
    stock["sentiment"]["sources"][0]["score"] = 0.42
    path.write_text(json.dumps(stock))
    assert_error(client.get("/api/stocks/TSLA"), 503, "data_unavailable")


def test_null_forecast_and_single_source_are_served(client, data_copy):
    path = data_copy / "stocks" / "TSLA.json"
    stock = json.loads(path.read_text())
    stock["forecast"] = None
    stock["sentiment"]["sources"] = stock["sentiment"]["sources"][1:2]
    stock["sentiment"]["gap"] = None
    path.write_text(json.dumps(stock))
    response = client.get("/api/stocks/TSLA")
    assert response.status_code == 200
    assert response.json() == stock


def test_rewritten_file_is_served_without_restart(client, data_copy):
    path = data_copy / "stocks" / "TSLA.json"
    assert client.get("/api/stocks/TSLA").json()["name"] == "Tesla, Inc."
    stock = json.loads(path.read_text())
    stock["name"] = "Tesla"
    path.write_text(json.dumps(stock))
    later = time.time_ns() + 1_000_000_000
    os.utime(path, ns=(later, later))
    assert client.get("/api/stocks/TSLA").json()["name"] == "Tesla"


def test_cors_allows_the_web_origin(client):
    response = client.get("/api/tickers", headers={"Origin": "http://localhost:3000"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    other = client.get("/api/tickers", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in other.headers
