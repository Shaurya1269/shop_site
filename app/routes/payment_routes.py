"""
app/routes/payment_routes.py

All payment-related routes for ShopSite.

Blueprint prefix: /payment

Routes
------
POST /payment/initiate          — validate customer details, dispatch by method
GET  /payment/instructions      — show UPI / QR / Phone payment instructions
POST /payment/create-order      — (Razorpay AJAX) create Razorpay order, return JSON
POST /payment/verify            — (Razorpay AJAX) verify signature, create marketplace order
POST /payment/confirm           — UPI/QR/Phone "I Have Paid" → create order
POST /payment/webhook           — Razorpay webhook (CSRF-exempt, signature-verified)
GET  /payment/success           — success page
GET  /payment/failed            — failure page
"""

import logging
import os

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.extensions import csrf
from app.models.payment_model import create_payment_method, get_payment_methods
from app.utils.decorators import login_required
from app.utils.validators import validate_phone
from services.order_services import create_order
from services.payment_service import (
    calculate_cart_total,
    create_razorpay_order,
    get_cart_items,
    get_shop_for_cart,
    get_shop_payment_methods,
    update_order_payment_info,
    verify_razorpay_signature,
    verify_webhook_signature,
)

logger = logging.getLogger(__name__)

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")

# ─── constants ────────────────────────────────────────────────────────────────
MANUAL_METHODS = {"UPI", "QR", "Phone"}
OFFLINE_METHODS = {"COD", "Pickup"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _validate_customer_details(form):
    """
    Read and validate customer details from a Flask request form.
    Returns (customer_name, phone, address, error_message).
    error_message is None on success.
    """
    customer_name = form.get("customer_name", "").strip()
    phone = form.get("phone", "").strip()
    address = form.get("address", "").strip()

    if not customer_name:
        return None, None, None, "Full name is required."
    if not validate_phone(phone):
        return None, None, None, "Invalid phone number (10–15 digits)."
    if not address:
        return None, None, None, "Delivery address is required."

    return customer_name, phone, address, None


# ─────────────────────────────────────────────────────────────────────────────
# POST /payment/initiate — entry point for all non-Razorpay methods
# ─────────────────────────────────────────────────────────────────────────────


@payment_bp.route("/initiate", methods=["POST"])
@login_required
def initiate():
    """
    Validate customer details and dispatch based on payment method.

    - COD / Pickup  → create_order() immediately → success page
    - UPI / QR / Phone → store in session → instructions page
    - Razorpay      → should not reach here (JS handles it via /payment/create-order)
    """
    customer_name, phone, address, err = _validate_customer_details(request.form)
    if err:
        flash(err, "danger")
        return redirect("/checkout-page")

    payment_method = request.form.get("payment_method", "").strip()
    if not payment_method:
        flash("Please select a payment method.", "danger")
        return redirect("/checkout-page")

    user_id = session["user_id"]

    # Store customer details for downstream use (instructions page / confirm)
    session["checkout_data"] = {
        "customer_name": customer_name,
        "phone": phone,
        "address": address,
        "payment_method": payment_method,
    }

    # ── Offline (COD / Pickup) — create order immediately ────────────────────
    if payment_method in OFFLINE_METHODS:
        try:
            result = create_order(
                user_id=user_id,
                customer_name=customer_name,
                phone=phone,
                address=address,
                payment_method=payment_method,
                payment_status="Pending",
                order_status="Pending",
            )
            session.pop("checkout_data", None)
            return render_template(
                "store/order_success.html",
                order_id=result["order_id"],
                total=result["total"],
                payment_method=payment_method,
                payment_status="Pending",
            )
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect("/checkout-page")
        except Exception:
            logger.exception("[initiate] create_order failed for offline method")
            flash("Something went wrong. Please try again.", "danger")
            return redirect("/checkout-page")

    # ── Manual online (UPI / QR / Phone) — show instructions page ────────────
    if payment_method in MANUAL_METHODS:
        return redirect(url_for("payment.instructions"))

    # ── Razorpay came through the form (should not happen, but handle gracefully)
    if payment_method == "Razorpay":
        flash("Please use the Razorpay button to pay.", "danger")
        return redirect("/checkout-page")

    flash("Unknown payment method.", "danger")
    return redirect("/checkout-page")


# ─────────────────────────────────────────────────────────────────────────────
# GET /payment/instructions — UPI / QR / Phone payment instructions
# ─────────────────────────────────────────────────────────────────────────────


@payment_bp.route("/instructions", methods=["GET"])
@login_required
def instructions():
    """Show payment instructions for manual methods (UPI, QR Code, Phone)."""
    checkout_data = session.get("checkout_data")
    if not checkout_data:
        return redirect("/checkout-page")

    payment_method = checkout_data.get("payment_method")
    if payment_method not in MANUAL_METHODS:
        return redirect("/checkout-page")

    user_id = session["user_id"]
    items = get_cart_items(user_id)
    if not items:
        flash("Your cart is empty.", "danger")
        return redirect("/cart")

    total = sum(float(item["total"]) for item in items)
    shop_id = get_shop_for_cart(user_id)
    payment_info = get_shop_payment_methods(shop_id) if shop_id else None

    return render_template(
        "store/payment_instructions.html",
        payment_method=payment_method,
        payment_info=payment_info,
        items=items,
        total=total,
        customer_name=checkout_data.get("customer_name"),
        phone=checkout_data.get("phone"),
        address=checkout_data.get("address"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /payment/confirm — "I Have Paid" for manual methods
# ─────────────────────────────────────────────────────────────────────────────


@payment_bp.route("/confirm", methods=["POST"])
@login_required
def confirm():
    """
    Create the order after the customer confirms they have made a manual payment.
    Payment status is set to 'Awaiting Verification' so the seller can confirm.
    """
    checkout_data = session.get("checkout_data")
    if not checkout_data:
        flash("Session expired. Please start checkout again.", "danger")
        return redirect("/checkout-page")

    user_id = session["user_id"]

    try:
        result = create_order(
            user_id=user_id,
            customer_name=checkout_data["customer_name"],
            phone=checkout_data["phone"],
            address=checkout_data["address"],
            payment_method=checkout_data["payment_method"],
            payment_status="Awaiting Verification",
            order_status="Confirmed",
        )
        session.pop("checkout_data", None)
        return render_template(
            "store/order_success.html",
            order_id=result["order_id"],
            total=result["total"],
            payment_method=checkout_data["payment_method"],
            payment_status="Awaiting Verification",
        )
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect("/checkout-page")
    except Exception:
        logger.exception("[confirm] create_order failed")
        flash("Something went wrong. Please try again.", "danger")
        return redirect("/checkout-page")


# ─────────────────────────────────────────────────────────────────────────────
# POST /payment/create-order — Razorpay AJAX endpoint
# ─────────────────────────────────────────────────────────────────────────────


@payment_bp.route("/create-order", methods=["POST"])
@login_required
def razorpay_create_order():
    """
    Called by the checkout page JS when Razorpay is selected.
    Validates customer details, stores them in session, creates a Razorpay order,
    and returns JSON so the frontend can open the Razorpay checkout popup.

    Returns JSON:
        { razorpay_order_id, amount, currency, key }   on success
        { error: "..." }                                on failure
    """
    customer_name, phone, address, err = _validate_customer_details(request.form)
    if err:
        return jsonify({"error": err}), 400

    user_id = session["user_id"]

    # Cart must be non-empty
    total = calculate_cart_total(user_id)
    if total <= 0:
        return jsonify({"error": "Your cart is empty."}), 400

    # Store customer details — used later in /payment/verify after signature check
    session["checkout_data"] = {
        "customer_name": customer_name,
        "phone": phone,
        "address": address,
        "payment_method": "Razorpay",
    }

    try:
        amount_paise = int(round(total * 100))
        rzp_order = create_razorpay_order(
            amount_paise=amount_paise,
            currency="INR",
            receipt=f"user_{user_id}",
        )
        return jsonify(
            {
                "razorpay_order_id": rzp_order["id"],
                "amount": rzp_order["amount"],
                "currency": rzp_order["currency"],
                "key": os.environ.get("RAZORPAY_KEY_ID", ""),
            }
        )
    except RuntimeError as exc:
        logger.error(f"[razorpay_create_order] config error: {exc}")
        return jsonify({"error": "Razorpay is not configured. Contact the shop owner."}), 500
    except Exception:
        logger.exception("[razorpay_create_order] Razorpay API error")
        return jsonify({"error": "Could not initiate payment. Please try again."}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /payment/verify — Razorpay signature verification
# ─────────────────────────────────────────────────────────────────────────────


@payment_bp.route("/verify", methods=["POST"])
@login_required
def razorpay_verify():
    """
    Called by the checkout page JS after Razorpay payment completes.
    Verifies the HMAC-SHA256 signature and — only on success — creates the order.

    Expects form fields:
        razorpay_payment_id, razorpay_order_id, razorpay_signature

    Returns JSON:
        { success: true, redirect: "/payment/success?order_id=X" }
        { success: false, error: "..." }
    """
    razorpay_payment_id = request.form.get("razorpay_payment_id", "").strip()
    razorpay_order_id = request.form.get("razorpay_order_id", "").strip()
    razorpay_signature = request.form.get("razorpay_signature", "").strip()

    if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
        return jsonify({"success": False, "error": "Missing payment fields."}), 400

    # ── Verify signature — NEVER skip this ───────────────────────────────────
    if not verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
        logger.warning(
            f"[razorpay_verify] Signature mismatch for order_id={razorpay_order_id}"
        )
        return jsonify({"success": False, "error": "Payment verification failed."}), 400

    # ── Create marketplace order ONLY after verified ──────────────────────────
    checkout_data = session.get("checkout_data")
    if not checkout_data:
        return jsonify({"success": False, "error": "Session expired. Please try again."}), 400

    user_id = session["user_id"]

    try:
        result = create_order(
            user_id=user_id,
            customer_name=checkout_data["customer_name"],
            phone=checkout_data["phone"],
            address=checkout_data["address"],
            payment_method="Razorpay",
            payment_status="Paid",
            order_status="Confirmed",
            razorpay_payment_id=razorpay_payment_id,
            razorpay_order_id=razorpay_order_id,
        )
        session.pop("checkout_data", None)

        order_id = result["order_id"]
        redirect_url = url_for(
            "payment.success",
            order_id=order_id,
            total=f"{result['total']:.2f}",
            method="Razorpay",
        )
        return jsonify({"success": True, "redirect": redirect_url})

    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:
        logger.exception("[razorpay_verify] create_order failed after signature verified")
        return jsonify({"success": False, "error": "Order creation failed. Contact support."}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /payment/webhook — Razorpay webhook (CSRF-exempt)
# ─────────────────────────────────────────────────────────────────────────────


@payment_bp.route("/webhook", methods=["POST"])
@csrf.exempt
def razorpay_webhook():
    """
    Receive Razorpay webhook events.

    Supported events:
        payment.captured → set payment_status = 'Paid'
        payment.failed   → set payment_status = 'Failed'

    The webhook signature is always verified first.
    Orders are looked up by razorpay_order_id.
    """
    import json

    from app.utils.db import get_db_cursor as _get_cursor

    body_bytes = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not verify_webhook_signature(body_bytes, signature):
        logger.warning("[webhook] Invalid signature — rejected")
        return jsonify({"error": "Invalid signature"}), 400

    try:
        payload = json.loads(body_bytes)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400

    event = payload.get("event")
    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    razorpay_payment_id = payment_entity.get("id")
    razorpay_order_id = payment_entity.get("order_id")

    if not razorpay_order_id:
        return jsonify({"status": "ignored"}), 200

    # Determine new payment status
    if event == "payment.captured":
        new_payment_status = "Paid"
    elif event == "payment.failed":
        new_payment_status = "Failed"
    else:
        # Unhandled event — acknowledge and ignore
        return jsonify({"status": "ignored"}), 200

    # Update the order
    try:
        with _get_cursor() as (conn, cur):
            cur.execute(
                """
                UPDATE orders
                SET payment_status      = %s,
                    razorpay_payment_id = %s,
                    payment_time        = NOW()
                WHERE razorpay_order_id = %s
                """,
                (new_payment_status, razorpay_payment_id, razorpay_order_id),
            )
        logger.info(
            f"[webhook] event={event}  razorpay_order_id={razorpay_order_id}  "
            f"new_status={new_payment_status}"
        )
    except Exception:
        logger.exception("[webhook] DB update failed")
        return jsonify({"error": "DB error"}), 500

    return jsonify({"status": "ok"}), 200


# ─────────────────────────────────────────────────────────────────────────────
# GET /payment/success
# ─────────────────────────────────────────────────────────────────────────────


@payment_bp.route("/success")
@login_required
def success():
    """Payment & order success page."""
    order_id = request.args.get("order_id")
    total = request.args.get("total")
    method = request.args.get("method", "")
    return render_template(
        "store/order_success.html",
        order_id=order_id,
        total=total,
        payment_method=method,
        payment_status="Paid" if method == "Razorpay" else "Pending",
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /payment/failed
# ─────────────────────────────────────────────────────────────────────────────


@payment_bp.route("/failed")
def failed():
    """Payment failure page."""
    reason = request.args.get("reason", "")
    return render_template("store/payment_failed.html", reason=reason)
