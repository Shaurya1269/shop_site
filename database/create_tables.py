"""Create database tables on the Render PostgreSQL instance.

Usage:
    python database/create_tables.py

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

# Render provides postgres:// but psycopg2 v2.9+ requires postgresql://
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql://", 1)

# Read the schema file
schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

with open(schema_path, 'r') as f:
    schema = f.read()

try:
    conn = psycopg2.connect(url)
    cur = conn.cursor()
    cur.execute(schema)
    conn.commit()
    cur.close()
    conn.close()
    print("Database tables created successfully!")
except psycopg2.Error as e:
    print(f"Database error: {e}")
    sys.exit(1)
