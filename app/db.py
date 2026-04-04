import os
import psycopg2


def get_db():
    url=os.getenv("postgresql://postgres:password@localhost:5432/shop_platform")
    
    if url.startswith("postgres://"):
        url=url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)
