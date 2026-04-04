from app.utils.db import get_db
import uuid


def create_shop(user_id, shop_name):
    conn = get_db()
    cur = conn.cursor()

    slug = generate_slug(shop_name)
    cur.execute("""
        INSERT INTO shops (user_id, shop_name, slug)
        VALUES (?,?,?)
        """,
                (user_id, shop_name, slug))

    shop_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()

    return {'id': shop_id, 'shop_name': shop_name, 'slug': slug}


def generate_slug(name):
    base = name.lower().replace(" ", "-")
    return f"{base}-{str(uuid.uuid4())[:6]}"
