from app.utils.db import get_db_cursor


def create_order_item(order_id, product_id, quantity):
    """Create an order item (without price snapshot)."""
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (%s, %s, %s, (SELECT price FROM products WHERE id = %s))
            RETURNING id
        """, (order_id, product_id, quantity, product_id))
        item_id = cur.fetchone()['id']

    return item_id

