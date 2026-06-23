import os
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv
from contextlib import contextmanager


load_dotenv()

url = os.getenv("DATABASE_URL")
if not url:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. "
        "Please set it in your .env file."
    )

if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

# Initialize ThreadedConnectionPool
pool = ThreadedConnectionPool(1, 10, url, connect_timeout=10)


def get_db():
    """Get a PostgreSQL database connection from the pool."""
    return pool.getconn()


def release_db(conn):
    """Release a connection back to the pool."""
    pool.putconn(conn)


def get_cursor(conn):
    """Get a cursor that returns rows as dictionaries."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


@contextmanager
def get_db_cursor():
    """Get a database connection and cursor inside a context manager.
    Automatically commits on success or rolls back on exception, and
    ensures connection and cursor are closed.
    """
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


