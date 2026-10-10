"""Reads artifact JSON from DATA_DIR and validates it before it is served."""

import json
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from .errors import DataUnavailable, NotFound
from .schemas import Stock, Tickers

log = logging.getLogger("sentifi.api")

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = "contracts/examples"

# path -> (mtime_ns, payload). A rewritten file is picked up without a restart.
_cache: dict[Path, tuple[int, dict[str, Any]]] = {}


def data_dir() -> Path:
    """DATA_DIR, resolved from the repo root when relative."""
    path = Path(os.environ.get("DATA_DIR") or DEFAULT_DATA_DIR)
    return path if path.is_absolute() else REPO_ROOT / path


def read_json(relative: str) -> dict[str, Any]:
    path = data_dir() / relative
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        log.error("Artifact missing: %s", path)
        raise DataUnavailable(f"{relative} is not available") from None
    except json.JSONDecodeError as exc:
        log.error("Artifact is not valid JSON: %s (%s)", path, exc)
        raise DataUnavailable(f"{relative} is not available") from None


def load(relative: str, model: type[BaseModel]) -> dict[str, Any]:
    """Return the file's JSON unchanged, after checking it against `model`."""
    path = data_dir() / relative
    try:
        mtime = path.stat().st_mtime_ns
    except FileNotFoundError:
        mtime = None
    cached = _cache.get(path)
    if cached and cached[0] == mtime:
        return cached[1]

    payload = read_json(relative)
    try:
        model.model_validate_json(json.dumps(payload))
    except ValidationError as exc:
        log.error("Artifact fails the contract: %s\n%s", path, exc)
        raise DataUnavailable(f"{relative} does not match the contract") from None
    if mtime is not None:
        _cache[path] = (mtime, payload)
    return payload


def tickers() -> dict[str, Any]:
    return load("tickers.json", Tickers)


def stock(symbol: str) -> dict[str, Any]:
    symbol = symbol.upper()
    if symbol not in {t["symbol"] for t in tickers()["tickers"]}:
        raise NotFound(f"Unknown symbol: {symbol}")
    return load(f"stocks/{symbol}.json", Stock)
