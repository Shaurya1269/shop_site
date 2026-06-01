"""
Run database migrations (safe to run multiple times — all ALTER TABLE statements
use IF NOT EXISTS so re-running won't break anything).

Usage:
    python database/migrate.py

Requires DATABASE_URL to be set in the .env file.
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")

if not url:
    print("ERROR: DATABASE_URL is not set in .env file.")
    sys.exit(1)

if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

MIGRATIONS = [
    # Migration 1 — add user_id to orders table (tracks which customer placed the order)
    """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='orders' AND column_name='user_id'
        ) THEN
            ALTER TABLE orders
                ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
        END IF;
    END $$;
    """,
]

try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    for i, migration in enumerate(MIGRATIONS, start=1):
        print(f"Running migration {i}...")
        cur.execute(migration)
    conn.commit()
    cur.close()
    conn.close()
    print("All migrations applied successfully!")
except psycopg2.Error as e:
    print(f"Database error: {e}")
    sys.exit(1)
