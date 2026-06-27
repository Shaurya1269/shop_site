"""
services/order_services.py

Single source of truth for order creation.
ALL payment paths must call create_order() — nothing else creates orders.

This service owns the full atomic transaction:
  validate cart → verify stock → create order row → insert order_items
  → reduce stock → clear cart → commit.
Rolls back completely on any failure.
"""

import logging
from app.utils.db import get_db, get_cursor, release_db

logger = logging.getLogger(__name__)


def create_order(
    user_id: int,
    customer_name: str,
    phone: str,
    address: str,
    payment_method: str,
    payment_status: str,
    order_status: str = "Pending",
    razorpay_payment_id: str = None,
    razorpay_order_id: str = None,
) -> dict:
    """
    Atomically create a marketplace order from the user's current cart.

    Steps
    -----
    1. Validate cart — non-empty, single shop only.
    2. Verify stock — every item must have sufficient stock.
    3. INSERT orders row.
    4. INSERT order_items rows.
    5. UPDATE products.stock (decrement).
    6. DELETE cart rows for this user.
    7. COMMIT.

    Returns
    -------
    dict with keys: order_id, shop_id, total, created_at

    Raises
    ------
    ValueError  — validation failures (empty cart, multi-shop, out-of-stock).
    Exception   — database errors (connection, constraint, etc.).
                  The transaction is always rolled back on any error.
    """
    conn = None
    cur = None
    try:
        conn = get_db()
        cur = get_cursor(conn)

        # ── 1. Validate cart — must be non-empty, single shop ────────────────
        cur.execute(
            """
            SELECT DISTINCT products.shop_id
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = %s
            """,
            (user_id,),
        )
        shops = cur.fetchall()

        if len(shops) == 0:
            raise ValueError("Cart is empty")
        if len(shops) > 1:
            raise ValueError("You can only order from one shop at a time")

        shop_id = shops[0]["shop_id"]

        # ── 2. Fetch cart items ───────────────────────────────────────────────
        cur.execute(
            """
            SELECT
                cart.id            AS cart_id,
                products.id        AS product_id,
                products.name      AS product_name,
                products.price,
                products.stock,
                cart.quantity
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = %s
            """,
            (user_id,),
        )
        cart_items = cur.fetchall()

        if not cart_items:
            raise ValueError("Cart is empty")

        # ── 3. Stock verification ─────────────────────────────────────────────
        for item in cart_items:
            if item["quantity"] > item["stock"]:
                raise ValueError(
                    f"Not enough stock for '{item['product_name']}'. "
                    f"Only {item['stock']} left."
                )

        # ── 4. Total ──────────────────────────────────────────────────────────
        total = sum(float(item["price"]) * item["quantity"] for item in cart_items)

        # ── 5. Create order row ───────────────────────────────────────────────
        cur.execute(
            """
            INSERT INTO orders (
                shop_id, user_id, customer_name, phone, address,
                status, payment_method, payment_status,
                razorpay_payment_id, razorpay_order_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
            """,
            (
                shop_id,
                user_id,
                customer_name,
                phone,
                address,
                order_status,
                payment_method,
                payment_status,
                razorpay_payment_id,
                razorpay_order_id,
            ),
        )
        order_row = cur.fetchone()
        order_id = order_row["id"]

        # ── 6. Insert order items + reduce stock ──────────────────────────────
        for item in cart_items:
            price = float(item["price"])

            cur.execute(
                """
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
                """,
                (order_id, item["product_id"], item["quantity"], price),
            )

            cur.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (item["quantity"], item["product_id"]),
            )

        # ── 7. Clear cart ─────────────────────────────────────────────────────
        cur.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))

        # ── 8. Commit ─────────────────────────────────────────────────────────
        conn.commit()

        logger.info(
            f"[create_order] SUCCESS order_id={order_id}  user_id={user_id}  "
            f"shop_id={shop_id}  total={total:.2f}  payment_method={payment_method}"
        )

        return {
            "order_id": order_id,
            "shop_id": shop_id,
            "total": total,
            "created_at": order_row["created_at"],
        }

    except Exception:
        # Roll back the entire transaction — leave no partial data
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise

    finally:
        if cur:
            try:
                cur.close()
            except Exception:
                pass
        if conn:
            try:
                release_db(conn)
            except Exception:
                pass
