import os
from contextlib import contextmanager
from psycopg2 import pool

_POOL = None


def _get_pool():
    global _POOL
    if _POOL is None:
        _POOL = pool.SimpleConnectionPool(
            1, 10,
            dbname=os.environ.get("PGDATABASE", "eduai_test"),
            user=os.environ.get("PGUSER", "postgres"),
            host=os.environ.get("PGHOST", "/var/run/postgresql"),
        )
    return _POOL


@contextmanager
def get_cursor(commit: bool = False):
    """Fournit un curseur avec commit/rollback automatique. `commit=True`
    pour les endpoints qui écrivent, `commit=False` (défaut) pour les
    lectures — évite d'ouvrir des transactions inutiles sur les GET.
    """
    conn = _get_pool().getconn()
    try:
        cur = conn.cursor()
        yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        _get_pool().putconn(conn)
