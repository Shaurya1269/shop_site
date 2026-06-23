import logging
import traceback
from flask import Blueprint, session, redirect, render_template, jsonify
from app.utils.db import get_db_cursor
from app.utils.decorators import login_required

logger = logging.getLogger(__name__)
order_bp = Blueprint("order", __name__)


@order_bp.route('/my-orders')
@login_required
def my_orders():
    """View orders placed BY the current user (as a customer)."""
    user_id = session['user_id']
    logger.info(f"[my_orders] fetching orders for user_id={user_id}")

    try:
        with get_db_cursor() as (conn, cur):
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
                order_dict['total'] = sum(float(i['price']) * i['quantity'] for i in items)
                orders_list.append(order_dict)

        return render_template("dashboard/orders.html", orders=orders_list, is_shop_owner=False)

    except Exception as exc:
        tb = traceback.format_exc()
        logger.error(f"[my_orders] EXCEPTION:\n{tb}")
        return "Something went wrong loading your orders. Please try again later.", 500


@order_bp.route("/update-order-status/<int:order_id>/<status>", methods=["POST"])
@login_required
def update_order_status(order_id, status):
    allowed_statuses = [
        "Pending", "Accepted", "Shipped", "Delivered", "Cancelled"
    ]
    if status not in allowed_statuses:
        return "Invalid Status", 400

    with get_db_cursor() as (conn, cur):
        # Verify authorization: current user must own the shop this order belongs to
        cur.execute("""
            SELECT shops.user_id 
            FROM orders
            JOIN shops ON orders.shop_id = shops.id
            WHERE orders.id = %s
        """, (order_id,))
        shop = cur.fetchone()
        
        if not shop or shop["user_id"] != session["user_id"]:
            return "Unauthorized", 403

        cur.execute("UPDATE orders SET status = %s WHERE id = %s", (status, order_id))

    return redirect("/orders")