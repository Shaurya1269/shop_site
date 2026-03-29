from app.utils.db import get_db
import uuid

def create_shop(user_id, shop_name):
    conn = get_db()
    cur = conn.cursor()

    slug = generate_slug(shop_name)
    cur.execute("""
        INSERT INTO shops (user_id, shop_name, slug)
        VALUES (%s,%s,%s)
        RETURNING id, shop_name, slug
        """,
                (user_id, shop_name, slug))

    shop = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return shop

def generate_slug(name):
    base=name.lower().replace(" ","-")
    return f"{base}-{str(uuid.uuid4())[:6]}"