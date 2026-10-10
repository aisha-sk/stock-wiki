"""Load ``ml/config.yaml``."""

from dataclasses import dataclass
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


@dataclass(frozen=True)
class Ticker:
    symbol: str
    name: str


@dataclass(frozen=True)
class Config:
    tickers: tuple[Ticker, ...]
    horizon_days: int
    history_years: int
    sentiment_window_days: int
    gate_threshold: float
    prices_in_payload: int


def load_config(path: Path | None = None) -> Config:
    """Read the pipeline config. Tickers stay in file order."""
    config_path = path or CONFIG_PATH
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    tickers = tuple(
        Ticker(symbol=str(symbol), name=str(name)) for symbol, name in raw["tickers"].items()
    )
    return Config(
        tickers=tickers,
        horizon_days=int(raw["horizon_days"]),
        history_years=int(raw["history_years"]),
        sentiment_window_days=int(raw["sentiment_window_days"]),
        gate_threshold=float(raw["gate"]["threshold"]),
        prices_in_payload=int(raw["prices_in_payload"]),
    )
