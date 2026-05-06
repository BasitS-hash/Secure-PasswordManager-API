"""
Database connection and query utilities.
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')


def get_connection():
    """Get a database connection."""
    return psycopg2.connect(DATABASE_URL)


def query(sql, params=None):
    """Execute a query and return results."""
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        conn.commit()

        # Return results or None for INSERT/UPDATE/DELETE
        try:
            return cur.fetchall()
        except psycopg2.ProgrammingError:
            return None
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def query_one(sql, params=None):
    """Execute a query and return first result."""
    results = query(sql, params)
    return results[0] if results else None


def execute(sql, params=None):
    """Execute a statement (for INSERT, UPDATE, DELETE)."""
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
        conn.close()
