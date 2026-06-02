import os
from typing import Optional
import psycopg2
import psycopg2.extras
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise EnvironmentError("DATABASE_URL environment variable is required")
        _pool = psycopg2.pool.ThreadedConnectionPool(2, 10, DATABASE_URL)
    return _pool


def get_connection():
    return _get_pool().getconn()


def release_connection(conn):
    _get_pool().putconn(conn)


def query(sql, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        conn.commit()
        try:
            return cur.fetchall()
        except psycopg2.ProgrammingError:
            return None
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_connection(conn)


def query_one(sql, params=None):
    results = query(sql, params)
    return results[0] if results else None


def execute(sql, params=None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        return cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_connection(conn)
