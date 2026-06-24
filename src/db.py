"""Database connection and query utilities.

Uses a thread-safe connection pool so each request reuses a pooled connection
instead of opening a fresh TCP/auth handshake to PostgreSQL on every query.
All callers pass parameters separately (``%s`` placeholders) — never string
interpolation — so the driver parameterises queries and SQL injection is not
possible.
"""

import os
import threading
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from psycopg2 import pool as pg_pool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_POOL_MIN = int(os.getenv("DB_POOL_MIN", "1"))
_POOL_MAX = int(os.getenv("DB_POOL_MAX", "10"))

_pool: pg_pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> pg_pool.ThreadedConnectionPool:
    """Lazily create the connection pool (so importing the module is cheap)."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                if not DATABASE_URL:
                    raise RuntimeError("DATABASE_URL is not set")
                _pool = pg_pool.ThreadedConnectionPool(
                    _POOL_MIN, _POOL_MAX, dsn=DATABASE_URL
                )
    return _pool


@contextmanager
def _connection():
    """Yield a pooled connection, returning it to the pool on exit."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def query(sql, params=None):
    """Execute a query and return all rows as dicts, or None for non-SELECTs."""
    with _connection() as conn:
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params or ())
                # cur.description is None for statements with no result set
                # (INSERT/UPDATE/DELETE without RETURNING).
                rows = cur.fetchall() if cur.description is not None else None
            conn.commit()
            return rows
        except Exception:
            conn.rollback()
            raise


def query_one(sql, params=None):
    """Execute a query and return the first row, or None."""
    results = query(sql, params)
    return results[0] if results else None


def execute(sql, params=None):
    """Execute an INSERT/UPDATE/DELETE and return the affected row count."""
    with _connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                rowcount = cur.rowcount
            conn.commit()
            return rowcount
        except Exception:
            conn.rollback()
            raise


def close_pool() -> None:
    """Close all pooled connections (used on shutdown / in tests)."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
