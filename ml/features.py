"""Price features and the 5-day direction target.

Every feature on day *t* is computed from sessions up to and including *t*.
The target looks forward and is kept out of this module's feature columns.
"""

import pandas as pd

FEATURE_COLUMNS: tuple[str, ...] = (
    "ret_1d",
    "ret_5d",
    "ret_10d",
    "vol_10d",
    "vol_20d",
    "rsi_14",
    "volume_ratio",
    "sma20_gap",
)


def add_features(prices: pd.DataFrame) -> pd.DataFrame:
    """Add the model features. ``prices`` must already be sorted by date."""
    frame = prices.copy()
    close = pd.to_numeric(frame["close"])
    volume = pd.to_numeric(frame["volume"])
    frame["ret_1d"] = close.pct_change(1)
    frame["ret_5d"] = close.pct_change(5)
    frame["ret_10d"] = close.pct_change(10)
    frame["vol_10d"] = frame["ret_1d"].rolling(10, min_periods=10).std()
    frame["vol_20d"] = frame["ret_1d"].rolling(20, min_periods=20).std()
    frame["rsi_14"] = _rsi(close, 14)
    volume_mean = volume.rolling(20, min_periods=20).mean()
    frame["volume_ratio"] = volume / volume_mean - 1.0
    sma20 = close.rolling(20, min_periods=20).mean()
    frame["sma20_gap"] = close / sma20 - 1.0
    return frame


def add_target(frame: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    """Label day *t* as 1 when the close ``horizon`` sessions later is higher.

    The last ``horizon`` rows have no label. ``fwd_return_pct`` is in percent units.
    """
    labelled = frame.copy()
    future = labelled["close"].shift(-horizon)
    higher = future > labelled["close"]
    labelled["y"] = higher.astype(float).mask(future.isna())
    labelled["fwd_return_pct"] = (future / labelled["close"] - 1.0) * 100.0
    return labelled


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    relative_strength = avg_gain / avg_loss.where(avg_loss != 0)
    rsi = 100.0 - (100.0 / (1.0 + relative_strength))
    return rsi.mask((avg_loss == 0) & avg_gain.notna(), 100.0)
