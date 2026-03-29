from flask import session
from app.utils.db import get_db
from datetime import datetime


def create_order(user_id, shop_id, customer_name, phone, address):
    """Create a new order with customer details"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO orders (shop_id, customer_name, phone, address, created_at)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, shop_id, customer_name, phone, address, created_at
    """, (shop_id, customer_name, phone, address, datetime.now()))

    order = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return order


def validate_cart_single_shop(user_id):
    """Check if all cart items are from the same shop"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT products.shop_id
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (user_id,))

    shops = cur.fetchall()
    cur.close()
    conn.close()

    if len(shops) > 1:
        return None, "You can only order from one shop at a time"
    elif len(shops) == 0:
        return None, "Cart is empty"

    return shops[0]['shop_id'], None


def add_order_item(order_id, product_id, quantity, price):
    """Add item to order with price snapshot"""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO order_items (order_id, product_id, quantity, price)
        VALUES (%s, %s, %s, %s)
        RETURNING id, order_id, product_id, quantity, price
    """, (order_id, product_id, quantity, price))

    item = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return item
