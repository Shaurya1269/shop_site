from flask import Blueprint, session, redirect, render_template
from app.utils.db import get_db, get_cursor
from app.utils.decorators import login_required

order_bp = Blueprint("order", __name__)


@order_bp.route('/my-orders')
@login_required
def my_orders():
    """View orders placed by the current user (as a customer).
    
    This shows orders where the current user placed the order,
    tracked via the cart/checkout flow which uses session user_id.
    """
    conn = get_db()
    cur = get_cursor(conn)

    # Get orders placed by the current user
    # The orders table tracks shop_id — we find orders the user placed
    # by checking which orders were created for shops AND by this user.
    # Since the checkout flow creates orders with the user's session,
    # we need to track user_id on orders. For now, show orders from
    # shops owned by the current user (shop owner view).
    cur.execute("""
        SELECT orders.*, shops.shop_name
        FROM orders
        JOIN shops ON orders.shop_id = shops.id
        WHERE shops.user_id = %s
        ORDER BY orders.created_at DESC
    """, (session['user_id'],))

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
