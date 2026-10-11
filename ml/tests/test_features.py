"""Feature and target tests. No network, no model fitting."""

import numpy as np
import pandas as pd
import pytest

from ml.features import FEATURE_COLUMNS, add_features, add_target


def _prices_from_closes(closes: list[float]) -> pd.DataFrame:
    n = len(closes)
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-02", periods=n),
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [100.0] * n,
        }
    )


def test_future_rows_do_not_change_features_at_t() -> None:
    rng = np.random.default_rng(0)
    closes = (100 * np.cumprod(1 + rng.normal(0.0, 0.01, 80))).tolist()
    prices = _prices_from_closes(closes)
    prices["volume"] = rng.integers(1_000, 2_000, len(prices))

    as_of = prices.loc[40, "date"]
    before = add_features(prices)
    before_row = before.loc[before["date"] == as_of, list(FEATURE_COLUMNS)].iloc[0]

    changed = prices.copy()
    changed.loc[41:, ["open", "high", "low", "close", "volume"]] = (
        changed.loc[41:, ["open", "high", "low", "close", "volume"]] * 3
    )
    after = add_features(changed)
    after_row = after.loc[after["date"] == as_of, list(FEATURE_COLUMNS)].iloc[0]

    pd.testing.assert_series_equal(before_row, after_row, check_names=False)


def test_target_matches_hand_computed_value() -> None:
    prices = _prices_from_closes([10, 11, 12, 13, 14, 16, 15, 9])
    labelled = add_target(prices, horizon=5)

    assert "y" not in labelled.columns
    assert labelled.loc[0, "fwd_return_pct"] == pytest.approx(60.0)
    assert labelled.loc[2, "fwd_return_pct"] == pytest.approx(-25.0)
    assert labelled.loc[3:, "fwd_return_pct"].isna().all()


def test_news_lag1_uses_the_window_ending_yesterday() -> None:
    prices = _prices_from_closes([10, 11, 12, 13, 14])
    dates = list(prices["date"])
    documents = [
        {"published_at": dates[0].strftime("%Y-%m-%dT12:00:00Z"), "score": 40},
        {"published_at": dates[0].strftime("%Y-%m-%dT18:00:00Z"), "score": 20},
        {"published_at": dates[1].strftime("%Y-%m-%dT12:00:00Z"), "score": 100},
    ]

    featured = add_features(prices, news_documents=documents)
    later = add_features(
        prices,
        news_documents=[
            *documents,
            {"published_at": dates[2].strftime("%Y-%m-%dT12:00:00Z"), "score": -100},
        ],
    )

    assert featured.loc[0, "news_lag1"] != featured.loc[0, "news_lag1"]
    assert featured.loc[1, "news_lag1"] == 30
    assert featured.loc[2, "news_lag1"] == 53
    assert later.loc[1, "news_lag1"] == featured.loc[1, "news_lag1"]
    assert later.loc[2, "news_lag1"] == featured.loc[2, "news_lag1"]
