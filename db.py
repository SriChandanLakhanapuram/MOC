"""
db.py — Oracle Connection Pool
===============================
Manages a python-oracledb connection pool for the Examination Management System.
Uses context manager pattern to ensure connections are always released.
"""
import os
import oracledb
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Connection pool — created once at module import time.
# min=2  : two connections always warm (avoids first-request latency)
# max=10 : hard ceiling to protect Oracle XE resource limits
# increment=1 : grow one connection at a time under load
# ---------------------------------------------------------------------------
_pool = None


def _get_pool():
    """Create the Oracle pool on first use so documentation/FSM pages start
    even when the database is temporarily unavailable."""
    global _pool
    if _pool is None:
        _pool = oracledb.create_pool(
            user=os.getenv('ORACLE_USER', 'MOC_project'),
            password=os.getenv('ORACLE_PASSWORD', ''),
            dsn=os.getenv('ORACLE_DSN', 'localhost:1521/XEPDB1'),
            min=1, max=5, increment=1,
        )
    return _pool


@contextmanager
def get_db():
    """
    Yield a pooled Oracle connection.

    Usage::

        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT ...")

    * Commits on clean exit.
    * Rolls back and re-raises on any exception.
    * Always releases the connection back to the pool.
    """
    conn = _get_pool().acquire()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        _get_pool().release(conn)
