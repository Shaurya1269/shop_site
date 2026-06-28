"""
services/payment_service.py

All Razorpay SDK interactions and cart-query helpers live here.
Routes must NEVER import razorpay directly — use this module instead.
"""

import hashlib
import hmac
import logging
import os

import razorpay

from app.models.payment_model import get_payment_methods
from app.utils.db import get_db_cursor

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _razorpay_client(key_id: str = None, key_secret: str = None) -> razorpay.Client:
    """Return an authenticated Razorpay client.

    Falls back to environment variables if parameters are not provided.
    Raises RuntimeError if credentials are missing.
    """
    final_key_id = key_id or os.environ.get("RAZORPAY_KEY_ID", "")
    final_key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET", "")
    if not final_key_id or not final_key_secret:
        raise RuntimeError(
            "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in the environment or configured for the shop."
        )
    return razorpay.Client(auth=(final_key_id, final_key_secret))


# ─────────────────────────────────────────────────────────────────────────────
# Cart helpers
# ─────────────────────────────────────────────────────────────────────────────


def get_cart_items(user_id: int) -> list:
    """Return all cart items for the given user as a list of dicts."""
    with get_db_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT
                products.id        AS product_id,
                products.name,
                products.price,
                cart.quantity,
                (products.price * cart.quantity) AS total
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = %s
            """,
            (user_id,),
        )
        return cur.fetchall()


def calculate_cart_total(user_id: int) -> float:
    """Return the cart grand total as a float (₹), or 0.0 if empty."""
    items = get_cart_items(user_id)
    return sum(float(item["total"]) for item in items) if items else 0.0


def get_shop_for_cart(user_id: int):
    """Return the shop_id associated with the user's cart, or None."""
    with get_db_cursor() as (conn, cur):
        cur.execute(
            """
            SELECT DISTINCT products.shop_id
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()
    return row["shop_id"] if row else None


def get_shop_payment_methods(shop_id: int):
    """Thin wrapper so routes import only from payment_service."""
    return get_payment_methods(shop_id)


# ─────────────────────────────────────────────────────────────────────────────
# Razorpay order
# ─────────────────────────────────────────────────────────────────────────────


def create_razorpay_order(
    amount_paise: int,
    currency: str = "INR",
    receipt: str = None,
    key_id: str = None,
    key_secret: str = None,
) -> dict:
    """
    Create a Razorpay order.

    Parameters
    ----------
    amount_paise : int
        Amount in the smallest currency unit (paise for INR).
        e.g. ₹100.50  →  10050 paise.
    currency : str
        ISO 4217 currency code (default 'INR').
    receipt : str, optional
        Merchant-defined receipt identifier (≤40 chars).

    Returns
    -------
    dict — the Razorpay order object (contains 'id', 'amount', 'currency', …).
    """
    client = _razorpay_client(key_id=key_id, key_secret=key_secret)
    data: dict = {
        "amount": int(amount_paise),
        "currency": currency,
        "payment_capture": 1,  # auto-capture
    }
    if receipt:
        data["receipt"] = str(receipt)[:40]

    order = client.order.create(data=data)
    logger.info(
        f"[create_razorpay_order] created id={order['id']}  "
        f"amount={amount_paise}  currency={currency}"
    )
    return order


# ─────────────────────────────────────────────────────────────────────────────
# Signature verification
# ─────────────────────────────────────────────────────────────────────────────


def verify_razorpay_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    key_id: str = None,
    key_secret: str = None,
) -> bool:
    """
    Verify the HMAC-SHA256 signature returned by Razorpay after payment.

    Returns True on success, False on failure.
    Never raises — exceptions are caught and logged.
    """
    client = _razorpay_client(key_id=key_id, key_secret=key_secret)
    try:
        client.utility.verify_payment_signature(
            {
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            }
        )
        logger.info(
            f"[verify_razorpay_signature] OK  "
            f"order_id={razorpay_order_id}  payment_id={razorpay_payment_id}"
        )
        return True
    except Exception as exc:
        logger.warning(
            f"[verify_razorpay_signature] FAILED  "
            f"order_id={razorpay_order_id}  payment_id={razorpay_payment_id}  err={exc}"
        )
        return False


def verify_webhook_signature(body_bytes: bytes, signature: str) -> bool:
    """
    Verify the X-Razorpay-Signature header on incoming webhook requests.

    If RAZORPAY_WEBHOOK_SECRET is not configured, verification is skipped
    and True is returned with a warning (allows testing without secrets).
    """
    webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")
    if not webhook_secret:
        logger.warning(
            "[verify_webhook_signature] RAZORPAY_WEBHOOK_SECRET not set — "
            "skipping webhook signature verification."
        )
        return True

    expected = hmac.new(
        webhook_secret.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature or "")


# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────


def update_order_payment_info(
    order_id: int,
    razorpay_payment_id: str,
    razorpay_order_id: str,
    payment_status: str = None,
) -> None:
    """
    Persist Razorpay IDs (and optionally a new payment_status) on an existing order.

    Called by the webhook handler after a payment.captured / payment.failed event.
    """
    with get_db_cursor() as (conn, cur):
        if payment_status:
            cur.execute(
                """
                UPDATE orders
                SET razorpay_payment_id = %s,
                    razorpay_order_id   = %s,
                    payment_status      = %s,
                    payment_time        = NOW()
                WHERE id = %s
                """,
                (razorpay_payment_id, razorpay_order_id, payment_status, order_id),
            )
        else:
            cur.execute(
                """
                UPDATE orders
                SET razorpay_payment_id = %s,
                    razorpay_order_id   = %s,
                    payment_time        = NOW()
                WHERE id = %s
                """,
                (razorpay_payment_id, razorpay_order_id, order_id),
            )
    logger.info(
        f"[update_order_payment_info] order_id={order_id}  "
        f"razorpay_payment_id={razorpay_payment_id}  payment_status={payment_status}"
    )
