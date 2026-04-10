from app.utils.db import get_db, get_cursor


def create_order_item(order_id, product_id, quantity):
    """Create an order item (without price snapshot)."""
    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        INSERT INTO order_items (order_id, product_id, quantity, price)
        VALUES (%s, %s, %s, (SELECT price FROM products WHERE id = %s))
        RETURNING id
    """, (order_id, product_id, quantity, product_id))

    item_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    return item_id
