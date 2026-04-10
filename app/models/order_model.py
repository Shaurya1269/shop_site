from app.utils.db import get_db, get_cursor
from datetime import datetime


def create_order(user_id, shop_id, customer_name, phone, address):
    """Create a new order with customer details."""
    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        INSERT INTO orders (shop_id, customer_name, phone, address)
        VALUES (%s, %s, %s, %s)
        RETURNING id, created_at
    """, (shop_id, customer_name, phone, address))

    result = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {
        'id': result['id'],
        'shop_id': shop_id,
        'customer_name': customer_name,
        'phone': phone,
        'address': address,
        'created_at': result['created_at']
    }


def validate_cart_single_shop(user_id):
    """Check if all cart items are from the same shop.
    
    Returns:
        (shop_id, None) if all items are from one shop.
        (None, error_message) if cart is empty or has items from multiple shops.
    """
    conn = get_db()
    cur = get_cursor(conn)

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
    """Add an item to an order with a price snapshot."""
    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        INSERT INTO order_items (order_id, product_id, quantity, price)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (order_id, product_id, quantity, price))

    item_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    return {
        'id': item_id,
        'order_id': order_id,
        'product_id': product_id,
        'quantity': quantity,
        'price': price
    }
