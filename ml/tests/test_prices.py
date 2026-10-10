"""Offline price-ingestion tests. No network."""

from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal

from ml.ingest.prices import (
    clean_prices,
    filter_completed_sessions,
    from_yfinance,
    load_prices,
)

FIXTURE = Path(__file__).parent / "fixtures" / "prices_sample.csv"


def test_clean_prices_sorts_dedupes_and_drops_missing_closes() -> None:
    cleaned = clean_prices(pd.read_csv(FIXTURE))

    assert list(cleaned.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert list(cleaned["date"].dt.strftime("%Y-%m-%d")) == [
        "2026-10-07",
        "2026-10-08",
        "2026-10-09",
    ]
    assert cleaned["date"].is_monotonic_increasing
    assert not cleaned["date"].duplicated().any()
    assert not cleaned["close"].isna().any()
    october_8 = cleaned.loc[cleaned["date"] == pd.Timestamp("2026-10-08"), "close"]
    assert float(october_8.iloc[0]) == 10.5


def test_filter_drops_the_bar_while_its_session_is_still_open() -> None:
    calendar = mcal.get_calendar("XNYS")
    schedule = calendar.schedule(start_date="2026-10-05", end_date="2026-10-09")
    session = schedule.index[-1]
    during = schedule.loc[session, "market_open"] + pd.Timedelta(minutes=1)
    after = schedule.loc[session, "market_close"] + pd.Timedelta(minutes=1)
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(schedule.index),
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 1.0,
        }
    )

    while_open = filter_completed_sessions(frame, now=during)
    after_close = filter_completed_sessions(frame, now=after)

    assert while_open["date"].max() < pd.Timestamp(session)
    assert after_close["date"].max() == pd.Timestamp(session)


def test_from_yfinance_flattens_single_ticker_columns() -> None:
    index = pd.to_datetime(["2026-10-08", "2026-10-09"])
    columns = pd.MultiIndex.from_tuples(
        [
            ("Open", "TSLA"),
            ("High", "TSLA"),
            ("Low", "TSLA"),
            ("Close", "TSLA"),
            ("Volume", "TSLA"),
        ],
        names=["Price", "Ticker"],
    )
    raw = pd.DataFrame(
        [[1, 1, 1, 1, 10], [2, 2, 2, 2, 20]],
        index=index,
        columns=columns,
    )

    cleaned = clean_prices(from_yfinance(raw))

    assert list(cleaned["close"]) == [1, 2]
    assert list(cleaned["volume"]) == [10, 20]


def test_load_prices_reads_cache_without_calling_fetcher(tmp_path: Path) -> None:
    cached = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-10-08", "2026-10-09"]),
            "open": [1.0, 2.0],
            "high": [1.0, 2.0],
            "low": [1.0, 2.0],
            "close": [1.0, 2.0],
            "volume": [10.0, 20.0],
        }
    )
    cached.to_parquet(tmp_path / "TSLA.parquet", index=False)

    def fetcher(_symbol: str) -> pd.DataFrame:
        raise AssertionError("fetcher should not be called when the cache exists")

    loaded = load_prices("tsla", cache_dir=tmp_path, fetcher=fetcher)

    assert len(loaded) == 2
    assert list(loaded["close"]) == [1.0, 2.0]


def test_load_prices_fetches_once_and_second_read_matches(tmp_path: Path) -> None:
    calls: list[str] = []

    def fetcher(symbol: str) -> pd.DataFrame:
        calls.append(symbol)
        return pd.DataFrame(
            {
                "date": ["2026-10-08", "2026-10-09", "2026-10-08"],
                "open": [1, 2, 1],
                "high": [1, 2, 1],
                "low": [1, 2, 1],
                "close": [1.0, 2.0, 1.5],
                "volume": [10, 20, 15],
            }
        )

    now = pd.Timestamp("2026-10-10 12:00", tz="America/New_York")
    loaded = load_prices("TSLA", cache_dir=tmp_path, fetcher=fetcher, now=now)
    again = load_prices("TSLA", cache_dir=tmp_path, fetcher=fetcher, now=now)

    assert calls == ["TSLA"]
    assert list(loaded["date"].dt.strftime("%Y-%m-%d")) == ["2026-10-08", "2026-10-09"]
    october_8 = loaded.loc[loaded["date"] == pd.Timestamp("2026-10-08"), "close"]
    assert float(october_8.iloc[0]) == 1.5
    assert len(again) == len(loaded)
    assert (tmp_path / "TSLA.parquet").exists()
