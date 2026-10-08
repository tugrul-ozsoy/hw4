"""Database connections for the Campus Customs API.

Catalogue endpoints use a read-only connection. Only the account endpoints get a writable one.
Set CAMPUS_DB_PATH to point the app at another copy of the database (the tests use a temp copy).
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("CAMPUS_DB_PATH", ROOT / "data" / "campus_customs.db")).resolve()
IMAGES_DIR = ROOT / "data" / "products"


def _connect(read_only: bool) -> sqlite3.Connection:
    # FastAPI may open a dependency and run the endpoint on different thread-pool threads, so the
    # same-thread check is off; each connection still serves exactly one request.
    target = f"{DB_PATH.as_uri()}?mode=ro" if read_only else f"{DB_PATH.as_uri()}?mode=rw"
    conn = sqlite3.connect(target, uri=True, check_same_thread=False, timeout=5)
    conn.row_factory = sqlite3.Row
    if not read_only:
        conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def read_only_connection() -> Iterator[sqlite3.Connection]:
    """Read-only connection for code outside a request (the agent's tools)."""
    conn = _connect(read_only=True)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def writable_connection() -> Iterator[sqlite3.Connection]:
    """Writable connection (foreign keys on) for saving chat history."""
    conn = _connect(read_only=False)
    try:
        yield conn
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """Read-only connection, one per request."""
    conn = _connect(read_only=True)
    try:
        yield conn
    finally:
        conn.close()


def get_db_rw() -> Iterator[sqlite3.Connection]:
    """Writable connection for account endpoints (sign-up, password upgrades)."""
    conn = _connect(read_only=False)
    try:
        yield conn
    finally:
        conn.close()
