from app.utils.db import get_db, get_cursor
import uuid


def create_shop(user_id, shop_name, category=None, description=None):
    """Create a new shop for a user with a unique slug."""
    conn = get_db()
    cur = get_cursor(conn)

    slug = generate_slug(shop_name)
    cur.execute("""
        INSERT INTO shops (user_id, shop_name, slug, category, description)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (user_id, shop_name, slug, category, description))

    shop_id = cur.fetchone()['id']

    cur.execute("""
    INSERT INTO payment_methods(shop_id)
    VALUES(%s)
    """,(shop_id,))
    conn.commit()
    cur.close()
    conn.close()

    return {'id': shop_id, 'shop_name': shop_name, 'slug': slug}


def generate_slug(name):
    """Generate a URL-safe slug from a shop name with a unique suffix."""
    import re
    base = name.lower().strip()
    base = re.sub(r'[^\w\s-]', '', base)  # strip non-word chars except spaces/dashes
    base = re.sub(r'[\s_]+', '-', base)   # replace spaces/underscores with dash
    base = re.sub(r'-+', '-', base).strip('-')  # collapse multiple dashes
    return f"{base}-{str(uuid.uuid4())[:6]}"
