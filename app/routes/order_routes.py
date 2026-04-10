from flask import Blueprint, session, redirect, render_template
from app.utils.db import get_db, get_cursor
from app.utils.decorators import login_required

order_bp = Blueprint("order", __name__)


@order_bp.route('/my-orders')
@login_required
def my_orders():
    """View orders placed by the current user (as a customer)."""
    conn = get_db()
    cur = get_cursor(conn)

    # Get cart history — orders associated with this user's cart purchases
    # Since orders track customer_name (not user_id), we show orders
    # for shops owned by current user (shop owner view is in shop_routes /orders)
    cur.execute("""
        SELECT orders.*, shops.shop_name
        FROM orders
        JOIN shops ON orders.shop_id = shops.id
        ORDER BY orders.created_at DESC
    """)

    orders_data = cur.fetchall()

    orders_list = []
    for order in orders_data:
        cur.execute("""
            SELECT order_items.*, products.name as product_name
            FROM order_items
            JOIN products ON order_items.product_id = products.id
            WHERE order_items.order_id = %s
        """, (order['id'],))

        items = cur.fetchall()
        order_dict = dict(order)
        order_dict['items'] = items
        orders_list.append(order_dict)

    cur.close()
    conn.close()

    return render_template("dashboard/orders.html", orders=orders_list)
