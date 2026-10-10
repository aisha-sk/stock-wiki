"""Walk-forward split tests. Synthetic prices only."""

import numpy as np
import pandas as pd

from ml.features import FEATURE_COLUMNS, add_features, add_target
from ml.train import XGB_PARAMS, walk_forward, walk_forward_pooled


def _synthetic_prices(n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    close = 100 * np.cumprod(1 + rng.normal(0.0005, 0.01, n))
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2022-01-03", periods=n),
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": rng.integers(1_000, 2_000, n).astype(float),
        }
    )


def test_test_dates_are_outside_the_training_window_and_five_rows_are_purged() -> None:
    prices = _synthetic_prices()
    featured = add_target(add_features(prices), horizon=5)
    eligible = featured.dropna(subset=[*FEATURE_COLUMNS, "y"])
    eligible_dates = [pd.Timestamp(value) for value in eligible["date"]]

    result = walk_forward(prices, symbol="TEST", horizon=5)

    assert result.folds
    predicted = {pd.Timestamp(value) for value in result.predictions["as_of_date"]}
    tested: set[pd.Timestamp] = set()
    for fold in result.folds:
        train_dates = [pd.Timestamp(value) for value in fold.train_dates]
        test_dates = [pd.Timestamp(value) for value in fold.test_dates]
        assert set(test_dates).isdisjoint(train_dates)
        assert max(train_dates) < min(test_dates)
        test_start = eligible_dates.index(min(test_dates))
        train_end = eligible_dates.index(max(train_dates))
        assert test_start - train_end == 6
        tested.update(test_dates)

    assert predicted == tested


def test_pooled_folds_use_the_same_dates_for_every_ticker() -> None:
    left = _synthetic_prices()
    right = _synthetic_prices()
    right["close"] = right["close"] * 1.2

    result = walk_forward_pooled({"AAA": left, "BBB": right}, horizon=5, algorithm="xgboost")

    counts = result.predictions.groupby("as_of_date")["symbol"].nunique()
    assert counts.min() == 2
    for fold in result.folds:
        assert set(fold.test_dates).isdisjoint(fold.train_dates)
        assert max(fold.train_dates) < min(fold.test_dates)


def test_xgboost_candidate_keeps_the_fixed_small_settings() -> None:
    assert XGB_PARAMS["n_estimators"] == 200
    assert XGB_PARAMS["max_depth"] == 3
    assert XGB_PARAMS["learning_rate"] == 0.05
    assert XGB_PARAMS["subsample"] == 0.8
