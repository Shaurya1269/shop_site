import psycopg2
import os

# Path to the database
db_path = os.path.join(os.path.dirname(__file__), '..', 'shop.db')

# Connect to SQLite database
conn = psycopg2.connect(os.getenv("postgresql://shaurya:WO9M0uxXeskbGy3Lm8RmgbrPNMycN749@dpg-d74e8h450q8c73duv8ig-a.oregon-postgres.render.com/shopplatform123"))
cur = conn.cursor()

# Read and execute the schema
with open('schema.sql', 'r') as f:
    schema = f.read()

cur.executescript(schema)

conn.commit()
cur.close()
conn.close()

print("Database tables created successfully!")
