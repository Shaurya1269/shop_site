import sqlite3
from app.config import DATABASE_URL


def get_db():
    conn = sqlite3.connect(DATABASE_URL.replace('sqlite:///', ''))
    conn.row_factory = sqlite3.Row  # To make rows behave like dicts
    return conn
