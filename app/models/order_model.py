from app.utils.db import get_db_cursor
import logging

logger = logging.getLogger(__name__)


def create_order(user_id, shop_id, customer_name, phone, address):
    """
    DEPRECATED — checkout() in shop_routes.py now handles order
    creation directly on its own single connection.
    This function is kept for backward-compatibility only.
    Do NOT call it from checkout() — it opens its own connection
    which breaks the atomic transaction guarantee.
    """
    logger.warning(
        "create_order() called as a standalone function — "
        "this bypasses the atomic transaction in checkout(). "
        "Prefer inline SQL inside checkout()."
    )
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            INSERT INTO orders (shop_id, user_id, customer_name, phone, address,status)
            VALUES (%s, %s, %s, %s, %s,'Pending')
            RETURNING id, created_at
        """, (shop_id, user_id, customer_name, phone, address))
        result = cur.fetchone()

    return {
        'id':            result['id'],
        'shop_id':       shop_id,
        'user_id':       user_id,
        'customer_name': customer_name,
        'phone':         phone,
        'address':       address,
        'created_at':    result['created_at'],
        'status': 'Pending'
    }


def validate_cart_single_shop(user_id):
    """Check if all cart items are from the same shop.

    Returns:
        (shop_id, None)           — all items from one shop.
        (None, error_message)     — cart empty or multi-shop.
    """
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            SELECT DISTINCT products.shop_id
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = %s
        """, (user_id,))
        shops = cur.fetchall()

    if len(shops) > 1:
        return None, "You can only order from one shop at a time"
    elif len(shops) == 0:
        return None, "Cart is empty"

    return shops[0]['shop_id'], None


def add_order_item(order_id, product_id, quantity, price):
    """
    DEPRECATED — checkout() in shop_routes.py now handles order_item
    insertion directly. This function is kept for backward-compatibility.
    """
    logger.warning(
        "add_order_item() called as a standalone function — "
        "this bypasses the atomic transaction in checkout()."
    )
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            INSERT INTO order_items (order_id, product_id, quantity, price)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (order_id, product_id, quantity, price))
        item_id = cur.fetchone()['id']

    return {
        'id':         item_id,
        'order_id':   order_id,
        'product_id': product_id,
        'quantity':   quantity,
        'price':      price
    }

