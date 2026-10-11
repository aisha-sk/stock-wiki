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
    eligible = featured.dropna(subset=[*FEATURE_COLUMNS, "fwd_return_pct"])
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


def test_move_cutoff_ignores_returns_inside_the_test_fold() -> None:
    prices = _synthetic_prices(80)
    result = walk_forward(
        prices, symbol="TEST", horizon=5, initial=30, block=10, step=10, purge=5
    )
    featured = add_target(add_features(prices), horizon=5)
    featured = featured.dropna(subset=[*FEATURE_COLUMNS, "fwd_return_pct"])
    fold = result.folds[0]
    train = featured[pd.to_datetime(featured["date"]).isin(fold.train_dates)]
    expected = float(np.median(np.abs(train["fwd_return_pct"].to_numpy(dtype=float))))
    got = result.predictions.loc[
        pd.to_datetime(result.predictions["as_of_date"]).isin(fold.test_dates),
        "typical_move_pct",
    ]
    assert np.allclose(got, expected)

    perturbed = prices.copy()
    test_start = pd.Timestamp(min(fold.test_dates))
    perturbed.loc[pd.to_datetime(perturbed["date"]) >= test_start, "close"] *= 3
    again = walk_forward(
        perturbed, symbol="TEST", horizon=5, initial=30, block=10, step=10, purge=5
    )
    again_got = again.predictions.loc[
        pd.to_datetime(again.predictions["as_of_date"]).isin(fold.test_dates),
        "typical_move_pct",
    ]
    assert np.allclose(again_got, expected)


def test_xgboost_candidate_keeps_the_fixed_small_settings() -> None:
    assert XGB_PARAMS["n_estimators"] == 200
    assert XGB_PARAMS["max_depth"] == 3
    assert XGB_PARAMS["learning_rate"] == 0.05
    assert XGB_PARAMS["subsample"] == 0.8
