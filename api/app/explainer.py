"""Runs the explain agent for POST /api/explain, with a cache and a call limit in front of it.

The agent lives in the repo-root `agent` package and needs the `anthropic` SDK plus a
credential. Both are optional: without them this endpoint answers 503 and the rest of the
API is unaffected.
"""

import logging
import os
import sys
import threading
import time
from typing import Any

from .errors import DataUnavailable
from .store import REPO_ROOT

log = logging.getLogger("stocksense.api")

MAX_CALLS_PER_MINUTE = 10

_lock = threading.Lock()
_recent_calls: list[float] = []
# (symbol, question, data timestamp) -> answer. New data means a new key, so answers never go stale.
_cache: dict[tuple[str, str, str], dict[str, Any]] = {}


def configured() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _run(symbol: str, question: str) -> dict[str, Any]:
    """Import the agent only when it is needed, so the API starts without it."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from agent.explain import explain

    return explain(symbol, question)


def answer(symbol: str, question: str, data_generated_at: str) -> dict[str, Any]:
    if not configured():
        raise DataUnavailable("The explainer is not set up on this server.")

    key = (symbol, question.lower(), data_generated_at)
    with _lock:
        if key in _cache:
            return _cache[key]
        now = time.monotonic()
        _recent_calls[:] = [t for t in _recent_calls if now - t < 60]
        if len(_recent_calls) >= MAX_CALLS_PER_MINUTE:
            raise DataUnavailable("The explainer is busy. Try again in a minute.")
        _recent_calls.append(now)

    try:
        result = _run(symbol, question)
    except ImportError:
        log.exception("Explainer dependencies are missing")
        raise DataUnavailable("The explainer is not set up on this server.") from None
    except Exception as exc:
        # Covers a declined or unsupported answer and every Anthropic API error. The detail
        # goes to the log; the reader only needs to know it did not work.
        log.exception("Explainer failed for %s: %s", symbol, type(exc).__name__)
        raise DataUnavailable("The explainer could not answer just now.") from None

    with _lock:
        _cache[key] = result
    return result
