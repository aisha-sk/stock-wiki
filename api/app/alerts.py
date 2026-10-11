"""Alert sign-ups (stored in SQLite, never emailed yet) and the example email."""

import os
import sqlite3
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .store import REPO_ROOT

DEFAULT_DB = "api/alerts.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    symbol TEXT NOT NULL,
    trigger TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (email, symbol, trigger)
)
"""


def db_path() -> Path:
    """ALERTS_DB, resolved from the repo root when relative."""
    path = Path(os.environ.get("ALERTS_DB") or DEFAULT_DB)
    return path if path.is_absolute() else REPO_ROOT / path


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(SCHEMA)
    return connection


def create(email: str, symbol: str, trigger: str) -> tuple[dict[str, Any], bool]:
    """Store a sign-up. Returns the row and whether it is new."""
    email = email.strip().lower()
    with closing(_connect()) as connection, connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO alerts (id, email, symbol, trigger, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                email,
                symbol,
                trigger,
                datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
        )
        created = cursor.rowcount == 1
        row = connection.execute(
            "SELECT id, email, symbol, trigger, created_at FROM alerts "
            "WHERE email = ? AND symbol = ? AND trigger = ?",
            (email, symbol, trigger),
        ).fetchone()
    return {**dict(row), "delivery": "mock"}, created


def _signed(score: int) -> str:
    return f"+{score}" if score > 0 else str(score)


def preview(stock: dict[str, Any]) -> dict[str, Any]:
    """The example email for one stock, built only from its published payload."""
    symbol = stock["symbol"]
    sentiment = stock["sentiment"]
    gap = sentiment["gap"]
    lines: list[str] = []

    # Lead with the source that moved most since the previous window.
    moved = [s for s in sentiment["sources"] if s["previous_score"] is not None]
    if moved:
        lead = max(moved, key=lambda s: abs(s["score"] - s["previous_score"]))
        change = lead["score"] - lead["previous_score"]
        if change == 0:
            line = f"{lead['display_name']} sentiment held at {_signed(lead['score'])}"
        else:
            line = (
                f"{lead['display_name']} sentiment moved from {_signed(lead['previous_score'])} "
                f"to {_signed(lead['score'])}"
            )
        line += f" over the last {sentiment['window_days']} days"
        others = [s for s in moved if s is not lead]
        if others:
            steady = min(others, key=lambda s: abs(s["score"] - s["previous_score"]))
            verb = "stayed at" if abs(steady["score"] - steady["previous_score"]) <= 5 else "moved to"
            line += f", while {steady['display_name']} {verb} {_signed(steady['score'])}"
        lines.append(line + ".")

    forecast = stock["forecast"]
    if forecast:
        lines.append(
            f"Model forecast, next {forecast['horizon_days']} trading days: "
            f"{'Larger-than-usual' if forecast['move'] == 'large' else 'Typical'} move "
            f"(typical is {forecast['typical_move_pct']}%), "
            f"{round(forecast['confidence'] * 100)}% confidence."
        )

    if not lines:
        lines.append(f"There is no sentiment change to report for {symbol} yet.")

    return {
        "symbol": symbol,
        "subject": f"{symbol} sentiment gap: {gap['points']} points" if gap else f"{symbol} sentiment update",
        "body_lines": lines,
        "is_demo_data": stock["is_demo_data"],
    }
