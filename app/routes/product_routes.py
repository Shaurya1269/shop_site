from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models.product_model import get_product_by_id, update_product, delete_product
from app.utils.decorators import login_required
from app.utils.db import get_db_cursor
from app.utils.validators import validate_product_name, validate_price, validate_stock

product_bp = Blueprint("product", __name__)


@product_bp.route("/product/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = get_product_by_id(product_id)
    if not product:
        return "Product not found", 404

    # Verify authorization: current user must own the shop this product belongs to
    with get_db_cursor() as (conn, cur):
        cur.execute("SELECT user_id FROM shops WHERE id = %s", (product["shop_id"],))
        shop = cur.fetchone()

    if not shop or shop["user_id"] != session["user_id"]:
        return "Unauthorized", 403

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price")
        description = request.form.get("description", "").strip()
        stock = request.form.get("stock")

        if not validate_product_name(name):
            flash("Invalid product name (must be between 1 and 150 characters).", "danger")
            return render_template("dashboard/edit_product.html", product=product)

        if not validate_price(price):
            flash("Price must be a non-negative number.", "danger")
            return render_template("dashboard/edit_product.html", product=product)

        if not validate_stock(stock):
            flash("Stock must be a non-negative integer.", "danger")
            return render_template("dashboard/edit_product.html", product=product)

        price = float(price)
        stock = int(stock)

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
    with get_db_cursor() as (conn, cur):
        cur.execute("SELECT user_id FROM shops WHERE id = %s", (product["shop_id"],))
        shop = cur.fetchone()

    if not shop or shop["user_id"] != session["user_id"]:
        return "Unauthorized", 403

    delete_product(product_id)
    return redirect(url_for("shop.dashboard"))

