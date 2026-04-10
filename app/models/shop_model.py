from app.utils.db import get_db, get_cursor
import uuid


def create_shop(user_id, shop_name):
    """Create a new shop for a user with a unique slug."""
    conn = get_db()
    cur = get_cursor(conn)

    slug = generate_slug(shop_name)
    cur.execute("""
        INSERT INTO shops (user_id, shop_name, slug)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (user_id, shop_name, slug))

    shop_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    return {'id': shop_id, 'shop_name': shop_name, 'slug': slug}


def generate_slug(name):
    """Generate a URL-safe slug from a shop name with a unique suffix."""
    base = name.lower().replace(" ", "-")
    return f"{base}-{str(uuid.uuid4())[:6]}"
