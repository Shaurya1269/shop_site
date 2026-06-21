from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.product_model import get_product_by_id, update_product, delete_product
from app.utils.decorators import login_required
from app.utils.db import get_db, get_cursor

product_bp = Blueprint("product", __name__)


@product_bp.route("/product/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return "Product not found", 404

    # Verify authorization: current user must own the shop this product belongs to
    conn = get_db()
    cur = get_cursor(conn)
    cur.execute("SELECT user_id FROM shops WHERE id = %s", (product["shop_id"],))
    shop = cur.fetchone()
    cur.close()
    conn.close()

    if not shop or shop["user_id"] != session["user_id"]:
        return "Unauthorized", 403

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        description = request.form.get("description")
        stock = request.form.get("stock")

        try:
            price = float(price)
            stock = int(stock) if stock is not None else 0
        except (ValueError, TypeError):
            flash("Price and stock must be a valid number", "danger")
            return render_template("dashboard/edit_product.html", product=product)

        image_url = None
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename != '':
                from cloudinary import uploader as cloudinary_uploader
                result = cloudinary_uploader.upload(file, folder="products")
                image_url = result.get("secure_url")

        update_product(
            product_id,
            name,
            price,
            description,
            stock,
            image_url
        )
        return redirect(url_for("shop.dashboard"))

    return render_template(
        "dashboard/edit_product.html",
        product=product
    )


@product_bp.route("/product/<int:product_id>/delete", methods=["POST"])
@login_required
def remove_product(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return "Product not found", 404

    # Verify authorization
    conn = get_db()
    cur = get_cursor(conn)
    cur.execute("SELECT user_id FROM shops WHERE id = %s", (product["shop_id"],))
    shop = cur.fetchone()
    cur.close()
    conn.close()

    if not shop or shop["user_id"] != session["user_id"]:
        return "Unauthorized", 403

    delete_product(product_id)
    return redirect(url_for("shop.dashboard"))
