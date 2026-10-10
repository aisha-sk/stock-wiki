"""Reddit failure path. No network."""

from ml.ingest.reddit import fetch_reddit


def test_reddit_429_omits_the_source(monkeypatch) -> None:
    monkeypatch.setattr("ml.ingest.reddit.time.sleep", lambda _seconds: None)

    class _Response:
        status_code = 429
        text = ""

    monkeypatch.setattr("ml.ingest.reddit.requests.get", lambda *_args, **_kwargs: _Response())

    assert fetch_reddit("TSLA", "Tesla, Inc.") is None
