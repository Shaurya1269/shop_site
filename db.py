from contextlib import contextmanager
from app.utils.db import get_db, get_cursor, release_db

@contextmanager
def get_db_cursor():
    conn = get_db()
    cur = get_cursor(conn)
    try:
        yield conn, cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        release_db(conn)
