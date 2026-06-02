import logging
import traceback
from flask import Blueprint, session, redirect, render_template, jsonify
from app.utils.db import get_db, get_cursor
from app.utils.decorators import login_required

logger = logging.getLogger(__name__)
order_bp = Blueprint("order", __name__)


@order_bp.route('/my-orders')
@login_required
def my_orders():
    """View orders placed BY the current user (as a customer)."""
    user_id = session['user_id']
    logger.info(f"[my_orders] fetching orders for user_id={user_id}")

    conn = None
    try:
        conn = get_db()
        cur  = get_cursor(conn)

        cur.execute("""
            SELECT orders.*, shops.shop_name
            FROM orders
            JOIN shops ON orders.shop_id = shops.id
            WHERE orders.user_id = %s
            ORDER BY orders.created_at DESC
        """, (user_id,))
        orders_data = cur.fetchall()
        logger.info(f"[my_orders] found {len(orders_data)} orders")

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
            order_dict['items'] = [dict(i) for i in items]
            orders_list.append(order_dict)

        cur.close()
        conn.close()
        return render_template("dashboard/orders.html", orders=orders_list, is_shop_owner=False)

    except Exception as exc:
        if conn:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass
        tb = traceback.format_exc()
        logger.error(f"[my_orders] EXCEPTION:\n{tb}")
        return f"<pre>Error loading orders.\n\n{tb}</pre>", 500


@order_bp.route("/debug-orders")
def debug_orders():
    """
    Diagnostic endpoint — dumps all orders and order_items as JSON.
    Safe to hit from the browser. Remove in production.
    """
    conn = get_db()
    cur  = get_cursor(conn)

    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = [dict(row) for row in cur.fetchall()]

    cur.execute("SELECT * FROM order_items ORDER BY id DESC")
    items = [dict(row) for row in cur.fetchall()]

    cur.close()
    conn.close()

    # Convert Decimal / datetime fields to str so they serialise cleanly
    import json
    from decimal import Decimal
    from datetime import datetime

    def default_serialiser(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Not serialisable: {type(obj)}")

    payload = json.dumps(
        {"orders": orders, "order_items": items},
        default=default_serialiser,
        indent=2
    )
    return payload, 200, {"Content-Type": "application/json"}

@order_bp.route("/update-order-status/<int:order_id>/<status>", methods=["POST"])
@login_required
def update_order_status(order_id, status):
    allowed_statuses = [
        "Pending", "Accepted", "Shipped", "Delivered", "Cancelled"
    ]
    if status not in allowed_statuses:
        return "Invalid Status", 400

    conn = get_db()
    cur = get_cursor(conn)
    
    # Verify authorization: current user must own the shop this order belongs to
    cur.execute("""
        SELECT shops.user_id 
        FROM orders
        JOIN shops ON orders.shop_id = shops.id
        WHERE orders.id = %s
    """, (order_id,))
    shop = cur.fetchone()
    
    if not shop or shop["user_id"] != session["user_id"]:
        cur.close()
        conn.close()
        return "Unauthorized", 403

    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/orders")