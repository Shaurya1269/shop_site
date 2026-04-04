import sqlite3
import os

# Path to the database
db_path = os.path.join(os.path.dirname(__file__), '..', 'shop.db')

# Connect to SQLite database
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Read and execute the schema
with open('schema.sql', 'r') as f:
    schema = f.read()

cur.executescript(schema)

conn.commit()
cur.close()
conn.close()

print("Database tables created successfully!")
