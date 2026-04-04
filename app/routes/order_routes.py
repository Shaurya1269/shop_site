from flask import Blueprint, session, redirect, url_for
from app.utils.db import get_db

order_bp = Blueprint("order", __name__)


@order_bp.route('/checkpoint')
def checkout():
    user_id = session.get("user_id")

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT c.product_id,p.price,p.shop_id from cart c join products p on c.product_id=p.id where c.user_id=?", (user_id,))

    items = cur.fetchall()

    if not items:
        return "Cart is empty"

    shop_ids = set(item[2] for item in items)
    if len(shop_ids) > 1:
        return "All items must be from the same shop to checkout"

    total = sum([item[1] for item in items])

    cur.execute(
        """insert into orders(user_id,total_price) values (?, ?)""", (user_id, total))

    order_id = cur.lastrowid

    for item in items:
        cur.execute("""insert into order_items(order_id,product_id,quantity,price) values (?, ?, ?, ?)""",
                    (order_id, item[0], 1, item[1]))

    cur.execute("delete from cart where user_id= ?", (user_id,))

    conn.commit()
    cur.close()
    conn.close()

    return [f"Order placed successfully. Order ID: {order_id}", f"Total Price: {total}"]
