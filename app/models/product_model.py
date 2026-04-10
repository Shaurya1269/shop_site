from app.utils.db import get_db, get_cursor


def create_product(shop_id, name, price, description):
    """Create a new product in a shop."""
    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        INSERT INTO products (shop_id, name, price, description)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (shop_id, name, price, description))

    product_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    return {'id': product_id}
