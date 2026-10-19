"""
db.py — Oracle Connection Pool
===============================
Manages a python-oracledb connection pool for the Examination Management System.
Uses context manager pattern to ensure connections are always released.
"""
import oracledb
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Connection pool — created once at module import time.
# min=2  : two connections always warm (avoids first-request latency)
# max=10 : hard ceiling to protect Oracle XE resource limits
# increment=1 : grow one connection at a time under load
# ---------------------------------------------------------------------------
pool = oracledb.create_pool(
    user='MOC_project',
    password='chandan',
    dsn='localhost:1521/XEPDB1',
    min=2,
    max=10,
    increment=1
)


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
    conn = pool.acquire()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.release(conn)
