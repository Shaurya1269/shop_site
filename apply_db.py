from app.utils.db import get_db, get_cursor
from dotenv import load_dotenv

load_dotenv()
conn = get_db()
cur = get_cursor(conn)
cur.execute("""
CREATE TABLE IF NOT EXISTS reviews(
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(product_id, user_id)
);
""")
conn.commit()
cur.close()
conn.close()
print("Applied schema successfully")
