import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_db():
    """Get a PostgreSQL database connection.
    
    Handles Render's postgres:// vs postgresql:// URL format difference.
    Returns a psycopg2 connection object.
    """
    url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please set it in your .env file."
        )

    # Render provides postgres:// but psycopg2 v2.9+ requires postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    conn = psycopg2.connect(url)
    return conn


def get_cursor(conn):
    """Get a cursor that returns rows as dictionaries.
    
    Usage:
        conn = get_db()
        cur = get_cursor(conn)
        cur.execute("SELECT * FROM users")
        rows = cur.fetchall()  # List of dicts
    """
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
