"""Offline checks for the ML config the rest of the pipeline reads."""

from ml.config import load_config


def test_config_matches_kickoff_values() -> None:
    config = load_config()

    assert [(ticker.symbol, ticker.name) for ticker in config.tickers] == [
        ("TSLA", "Tesla, Inc."),
        ("NVDA", "NVIDIA Corporation"),
        ("AAPL", "Apple Inc."),
    ]
    assert config.horizon_days == 5
    assert config.history_years == 2
    assert config.sentiment_window_days == 7
    assert config.gate_threshold == 0.52
    assert config.prices_in_payload == 120
