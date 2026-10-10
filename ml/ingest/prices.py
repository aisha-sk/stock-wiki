"""Daily OHLCV prices from yfinance, cached under ``ml/data/prices``."""

import argparse
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal
import yfinance as yf

from ml.config import load_config

PRICE_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def default_cache_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "prices"


def from_yfinance(raw: pd.DataFrame) -> pd.DataFrame:
    """Turn a yfinance download frame into date/OHLCV columns."""
    frame = raw.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        flattened = None
        for level in range(frame.columns.nlevels):
            values = {str(value).lower() for value in frame.columns.get_level_values(level)}
            if "close" in values:
                flattened = frame.columns.get_level_values(level)
                break
        if flattened is None:
            raise ValueError("yfinance frame has no Close column")
        frame.columns = flattened
    frame = frame.reset_index()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    if "date" not in frame.columns:
        for candidate in ("datetime", "index"):
            if candidate in frame.columns:
                frame = frame.rename(columns={candidate: "date"})
                break
    missing = [column for column in PRICE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"yfinance frame is missing columns: {missing}")
    return frame[PRICE_COLUMNS]


def clean_prices(frame: pd.DataFrame) -> pd.DataFrame:
    """Sort by session, drop missing closes, and keep the last row of a duplicate date."""
    cleaned = frame.copy()
    cleaned.columns = [str(column).strip().lower() for column in cleaned.columns]
    missing = [column for column in PRICE_COLUMNS if column not in cleaned.columns]
    if missing:
        raise ValueError(f"price frame is missing columns: {missing}")
    cleaned = cleaned[PRICE_COLUMNS]
    cleaned["date"] = _as_session_dates(cleaned["date"])
    for column in ("open", "high", "low", "close", "volume"):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")
    cleaned = cleaned.dropna(subset=["close"])
    cleaned = cleaned.drop_duplicates(subset=["date"], keep="last")
    return cleaned.sort_values("date").reset_index(drop=True)


def latest_completed_session_date(now: pd.Timestamp) -> date:
    """Last NYSE session whose official close is at or before ``now``."""
    now_utc = pd.Timestamp(now)
    if now_utc.tzinfo is None:
        now_utc = now_utc.tz_localize("UTC")
    else:
        now_utc = now_utc.tz_convert("UTC")
    calendar = mcal.get_calendar("XNYS")
    start = (now_utc - pd.Timedelta(days=21)).date()
    schedule = calendar.schedule(start_date=start, end_date=now_utc.date())
    if schedule.empty:
        raise RuntimeError("NYSE schedule is empty for the requested window")
    closed = schedule.loc[schedule["market_close"] <= now_utc]
    if closed.empty:
        raise RuntimeError("no completed NYSE session before now")
    return pd.Timestamp(closed.index[-1]).date()


def filter_completed_sessions(frame: pd.DataFrame, now: pd.Timestamp) -> pd.DataFrame:
    """Drop any bar from a session that has not closed yet."""
    cutoff = pd.Timestamp(latest_completed_session_date(now))
    session_dates = _as_session_dates(frame["date"])
    return frame.loc[session_dates <= cutoff].reset_index(drop=True)


def fetch_prices(symbol: str) -> pd.DataFrame:
    """Download adjusted daily bars covering ``history_years``."""
    config = load_config()
    today = pd.Timestamp.now(tz="America/New_York").normalize()
    start = today - pd.DateOffset(years=config.history_years)
    end = today + pd.Timedelta(days=1)
    raw = yf.download(
        symbol,
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        auto_adjust=True,
        progress=False,
        threads=False,
        group_by="column",
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"no price data returned for {symbol}")
    return from_yfinance(raw)


def load_prices(
    symbol: str,
    *,
    cache_dir: Path | None = None,
    fetcher: Callable[[str], pd.DataFrame] | None = None,
    now: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Load cached OHLCV, downloading and caching it on a miss.

    Columns are ``date, open, high, low, close, volume``, ascending, with no
    duplicate dates and no missing closes. Only completed NYSE sessions are kept.
    """
    symbol = symbol.upper()
    cache_dir = cache_dir or default_cache_dir()
    path = cache_dir / f"{symbol}.parquet"
    if path.exists():
        return clean_prices(pd.read_parquet(path))

    fetched = (fetcher or fetch_prices)(symbol)
    as_of = now if now is not None else pd.Timestamp.now(tz="UTC")
    cleaned = filter_completed_sessions(clean_prices(fetched), now=as_of)
    if cleaned.empty:
        raise RuntimeError(f"no completed sessions for {symbol}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cleaned.to_parquet(path, index=False)
    return cleaned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download and cache daily OHLCV prices.")
    parser.add_argument("--tickers", nargs="+", required=True)
    args = parser.parse_args(argv)
    for symbol in args.tickers:
        frame = load_prices(symbol)
        last = pd.Timestamp(frame["date"].iloc[-1]).strftime("%Y-%m-%d")
        print(f"{symbol.upper()}: {len(frame)} rows, last session {last}")
    return 0


def _as_session_dates(values: pd.Series) -> pd.Series:
    """Calendar date of each bar, keeping the printed date rather than shifting zones."""
    parsed = pd.to_datetime(values)
    if getattr(parsed.dt, "tz", None) is not None:
        parsed = pd.to_datetime(parsed.dt.strftime("%Y-%m-%d"))
    return parsed.dt.normalize()


if __name__ == "__main__":
    raise SystemExit(main())
