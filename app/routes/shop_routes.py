import cloudinary
from cloudinary import uploader
import logging
import traceback
from flask import Blueprint, render_template, session, redirect, request, flash
from app.models.product_model import create_product
from app.utils.db import get_db_cursor, get_db, get_cursor, release_db
from app.utils.decorators import login_required
from app.models.shop_model import create_shop
import os
from app.models.payment_model import get_payment_methods, create_payment_method, update_payment_method
from app.utils.validators import validate_shop_name, validate_product_name, validate_price, validate_stock, validate_phone, validate_upi

logger = logging.getLogger(__name__)
shop_bp = Blueprint('shop', __name__)


@shop_bp.route("/")
def home():
    try:
        with get_db_cursor() as (conn, cur):
            cur.execute("SELECT shop_name, slug ,description, logo_url,banner_url FROM shops")
            shops = cur.fetchall()
           
            cur.execute("""
            select products.id,products.name,products.price,products.image_url, shops.shop_name,shops.slug 
            from products join shops on products.shop_id=shops.id
            order by products.id desc limit 8
            """)
            featured_products=cur.fetchall()

        return render_template("index.html", shops=shops,featured_products=featured_products)

    except Exception as e:
        logger.error(f"[home] DB error: {e}")
        return render_template("index.html", shops=[],featured_products=[] ,db_error=str(e))
    


@shop_bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "")
    price = request.args.get("price", "")
    rating = request.args.get("rating", "")
    availability = request.args.get("availability", "")
    sort = request.args.get("sort", "newest")
    
    try:
        with get_db_cursor() as (conn, cur):
            # Fetch available categories for sidebar
            cur.execute("SELECT DISTINCT category FROM shops WHERE category IS NOT NULL AND category != ''")
            categories = [row['category'] for row in cur.fetchall()]

            shops = []
            products = []

            # Shops search (only if there's a text query, no filters apply to shops)
            if query and not any([category, price, rating, availability]):
                cur.execute("""
                    SELECT shop_name, slug FROM shops WHERE shop_name ILIKE %s
                """, (f"%{query}%",))
                shops = cur.fetchall()

            # Products search
            sql = """
                SELECT products.id, products.name,
                       products.price,
                       products.image_url,
                       shops.shop_name,
                       shops.slug as shop_slug,
                       COALESCE(AVG(reviews.rating), 0) as avg_rating
                FROM products
                JOIN shops ON products.shop_id = shops.id
                LEFT JOIN reviews ON products.id = reviews.product_id
                WHERE 1=1
            """
            params = []
            
            if query:
                sql += " AND products.name ILIKE %s"
                params.append(f"%{query}%")
                
            if category:
                sql += " AND shops.category = %s"
                params.append(category)
                
            if price:
                if price == "0-500":
                    sql += " AND products.price <= 500"
                elif price == "500-1000":
                    sql += " AND products.price > 500 AND products.price <= 1000"
                elif price == "1000+":
                    sql += " AND products.price > 1000"
                    
            if availability == "in_stock":
                sql += " AND products.stock > 0"
                
            sql += " GROUP BY products.id, shops.shop_name, shops.slug"
            
            if rating:
                try:
                    min_rating = float(rating)
                    sql += f" HAVING COALESCE(AVG(reviews.rating), 0) >= {min_rating}"
                except ValueError:
                    pass
                    
            if sort == "price_asc":
                sql += " ORDER BY products.price ASC"
            elif sort == "price_desc":
                sql += " ORDER BY products.price DESC"
            else:
                sql += " ORDER BY products.created_at DESC"
                
            cur.execute(sql, tuple(params))
            products = cur.fetchall()
    except Exception as e:
        logger.error(f"[search] DB error: {e}")
        categories = []
        shops = []
        products = []

    return render_template(
        "search_results.html",
        query=query,
        category=category,
        price=price,
        rating=rating,
        availability=availability,
        sort=sort,
        categories=categories,
        shops=shops,
        products=products
    )


@shop_bp.route("/health")
def health():
    """Diagnostic route to test database connection."""
    try:
        with get_db_cursor() as (conn, cur):
            cur.execute("SELECT 1")
            cur.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = [row['table_name'] for row in cur.fetchall()]

        return {
            "status": "ok",
            "database": "connected",
            "tables": tables,
            "DATABASE_URL_set": bool(os.getenv("DATABASE_URL"))
        }
    except Exception as e:
        return {
            "status": "error",
            "error": "Database connection failed. Check server logs.",
            "DATABASE_URL_set": bool(os.getenv("DATABASE_URL"))
        }, 500


@shop_bp.route('/login')
def login_page():
    return render_template('auth/login.html')


@shop_bp.route('/register')
def register_page():
    return render_template('auth/register.html')


@shop_bp.route('/dashboard')
@login_required
def dashboard():
    products = []
    orders = []
    with get_db_cursor() as (conn, cur):
        cur.execute("SELECT * FROM shops WHERE user_id = %s", (session['user_id'],))
        shop = cur.fetchone()

        if shop:
            cur.execute("SELECT * FROM products WHERE shop_id = %s", (shop['id'],))
            products = cur.fetchall()

            # Fetch recent orders for this shop with computed totals
            cur.execute("""
                SELECT orders.id, orders.user_id, orders.customer_name, orders.phone,
                       orders.address, orders.status, orders.created_at,
                       orders.payment_method, orders.payment_status,
                       COALESCE(SUM(order_items.quantity * order_items.price), 0) AS total
                FROM orders
                LEFT JOIN order_items ON order_items.order_id = orders.id
                WHERE orders.shop_id = %s
                GROUP BY orders.id
                ORDER BY orders.created_at DESC
                LIMIT 10
            """, (shop['id'],))
            orders = cur.fetchall()

    return render_template('dashboard/dashboard.html', shop=shop, products=products, orders=orders)

@shop_bp.route("/shop-settings", methods=["GET", "POST"])
@login_required
def shop_settings():
    with get_db_cursor() as (conn, cur):
        cur.execute(
            "Select * from shops where user_id=%s",(session["user_id"],)
        )
        shop=cur.fetchone()
    if not shop:
        return "shop not found",404

    if request.method=="POST":
        shop_name = request.form.get("shop_name", "").strip()
        description = request.form.get("description", "").strip()

        if not validate_shop_name(shop_name):
            flash("Invalid shop name (must be between 1 and 100 characters).", "danger")
            return render_template("dashboard/shop_settings.html",shop=shop)

        logo_url = shop["logo_url"]
        banner_url = shop["banner_url"]

        #upload logo
        if "logo" in request.files and request.files["logo"].filename != "":
            result=uploader.upload(
                request.files['logo'],
                folder="shop_logos"
            )
            logo_url=result["secure_url"]

        #upload banner
        if "banner" in request.files and request.files["banner"].filename != "":
            result=uploader.upload(
                request.files['banner'],
                folder="shop_banners"
            )
            banner_url=result["secure_url"]
    
        with get_db_cursor() as (conn, cur):
            cur.execute("""
            update shops set shop_name=%s,
            description=%s,
            logo_url=%s,
            banner_url=%s
            where id=%s
        """,(shop_name,description,logo_url,banner_url,shop["id"]))

        return redirect("/dashboard")

    return render_template("dashboard/shop_settings.html",shop=shop)    


@shop_bp.route('/create-shop', methods=['GET', 'POST'])
@login_required
def create_shop_page():
    if request.method == 'POST':
        shop_name = request.form.get("shop_name", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        
        if not validate_shop_name(shop_name):
            flash("Invalid shop name (must be between 1 and 100 characters).", "danger")
            return render_template("dashboard/create_shop.html")

        create_shop(session['user_id'], shop_name, category, description)
        return redirect("/dashboard")

    return render_template("dashboard/create_shop.html")


@shop_bp.route("/shop/<slug>")
def view_store(slug):
    """Public store page — anyone can view a shop by its slug."""
    with get_db_cursor() as (conn, cur):
        cur.execute("SELECT id, shop_name, slug , description, logo_url, banner_url FROM shops WHERE slug = %s", (slug,))
        shop = cur.fetchone()

        if not shop:
            return "Shop not found", 404

        cur.execute(
            "SELECT id, name, price, description, stock, image_url FROM products WHERE shop_id = %s",
            (shop['id'],)
        )
        products = cur.fetchall()

    return render_template("store/store.html", shop=shop, products=products)


@shop_bp.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    user_id = session.get("user_id")

    with get_db_cursor() as (conn, cur):
        cur.execute("SELECT id FROM shops WHERE user_id = %s", (user_id,))
        shop = cur.fetchone()

    if not shop:
        return "Create a shop first", 400

    shop_id = shop['id']

    if request.method == 'POST':
        name = request.form.get("name", "").strip()
        price = request.form.get('price')
        description = request.form.get('description', '').strip()
        stock = request.form.get("stock")
        image_url = request.form.get("image_url")

        if not validate_product_name(name):
            flash("Invalid product name (must be between 1 and 150 characters).", "danger")
            return render_template("dashboard/add_product.html")

        if not validate_price(price):
            flash("Price must be a non-negative number.", "danger")
            return render_template("dashboard/add_product.html")

        if not validate_stock(stock):
            flash("Stock must be a non-negative integer.", "danger")
            return render_template("dashboard/add_product.html")

        price = float(price)
        stock = int(stock)
        
        if "image" in request.files and request.files['image'].filename !="":
            file=request.files["image"]
            result= uploader.upload(
                file,
                folder="products",
            )
            image_url=result.get("secure_url")

        with get_db_cursor() as (conn, cur):
            cur.execute(
                """INSERT INTO products (shop_id, name, price, description, stock, image_url) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (shop_id, name, price, description, stock, image_url)
            )
        return redirect("/dashboard")

    return render_template("dashboard/add_product.html")


@shop_bp.route("/add-to-cart", methods=["POST"])
@shop_bp.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id=None):
    """Add a product to the user's cart. Accepts product_id from form data or URL."""
    if "user_id" not in session:
        return redirect("/login")

    if product_id is None:
        product_id = request.form.get("product_id")

    if not product_id:
        return "Product ID is required", 400

    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return "Invalid product ID", 400

    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("SELECT id, shop_id,stock FROM products WHERE id = %s", (product_id,))
    new_product = cur.fetchone()

    if not new_product:
        cur.close()
        conn.close()
        return "Product not found", 404

    if new_product["stock"]<=0:
        cur.close()
        conn.close()
        return "Product out of stock",400

    cur.execute("""
        SELECT DISTINCT products.shop_id
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (session["user_id"],))
    existing_shops = cur.fetchall()

    if existing_shops and existing_shops[0]["shop_id"] != new_product["shop_id"]:
        cur.close()
        conn.close()
        return "You can only order from one shop at a time. Clear your cart first.", 400

    cur.execute("""
        SELECT id, quantity FROM cart
        WHERE user_id = %s AND product_id = %s
    """, (session["user_id"], product_id))
    existing_item = cur.fetchone()

    if existing_item and existing_item['quantity'] >= new_product["stock"]:
        cur.close()
        conn.close()
        return f"You can only order maximum of {new_product['stock']} items of this product",400

    if existing_item:
        cur.execute("""
            UPDATE cart SET quantity = quantity + 1
            WHERE id = %s
        """, (existing_item["id"],))
    else:
        cur.execute("""
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (%s, %s, 1)
        """, (session["user_id"], product_id))

    conn.commit()
    cur.close()
    conn.close()

    referrer = request.referrer
    if referrer and referrer.startswith(request.host_url):
        return redirect(referrer)
    return redirect("/")


@shop_bp.route("/buy-now/<int:product_id>", methods=["POST"])
@login_required
def buy_now(product_id):
    """Add a single product to cart (clearing any cross-shop conflict) and go straight to checkout."""
    conn = get_db()
    cur = get_cursor(conn)

    # Fetch product
    cur.execute("SELECT id, shop_id, stock FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()

    if not product:
        cur.close()
        conn.close()
        flash("Product not found.", "danger")
        return redirect(f"/product/{product_id}")

    if product["stock"] <= 0:
        cur.close()
        conn.close()
        flash("Sorry, this product is out of stock.", "danger")
        return redirect(f"/product/{product_id}")

    # Get requested quantity
    try:
        quantity = int(request.form.get("quantity", 1))
        if quantity < 1:
            quantity = 1
    except ValueError:
        quantity = 1

    # Check if quantity exceeds stock
    if quantity > product["stock"]:
        quantity = product["stock"]

    # If the cart has items from a different shop, clear them first
    # (Buy Now is an intentional single-product purchase — start fresh)
    cur.execute("""
        SELECT DISTINCT products.shop_id
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (session["user_id"],))
    existing_shops = cur.fetchall()

    if existing_shops and existing_shops[0]["shop_id"] != product["shop_id"]:
        cur.execute("DELETE FROM cart WHERE user_id = %s", (session["user_id"],))

    # Check if already in cart
    cur.execute("""
        SELECT id, quantity FROM cart
        WHERE user_id = %s AND product_id = %s
    """, (session["user_id"], product_id))
    existing_item = cur.fetchone()

    if existing_item:
        new_qty = existing_item["quantity"] + quantity
        if new_qty > product["stock"]:
            new_qty = product["stock"]
        cur.execute("UPDATE cart SET quantity = %s WHERE id = %s", (new_qty, existing_item["id"]))
    else:
        cur.execute("""
            INSERT INTO cart (user_id, product_id, quantity)
            VALUES (%s, %s, %s)
        """, (session["user_id"], product_id, quantity))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/checkout-page")


@shop_bp.route("/update-cart", methods=["POST"])
@login_required
def update_cart():
    """Update quantity of a cart item or remove it."""
    cart_id_raw = request.form.get("cart_id")
    action = request.form.get("action")  # "increase", "decrease", or "remove"

    if not cart_id_raw or not action:
        flash("Missing parameters", "danger")
        return redirect("/cart")

    try:
        cart_id = int(cart_id_raw)
    except (ValueError, TypeError):
        flash("Invalid cart item.", "danger")
        return redirect("/cart")

    if action not in ("increase", "decrease", "remove"):
        flash("Invalid action.", "danger")
        return redirect("/cart")

    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT cart.id, cart.quantity, products.stock 
        FROM cart 
        JOIN products ON cart.product_id = products.id
        WHERE cart.id = %s AND cart.user_id = %s
    """, (cart_id, session["user_id"]))
    item = cur.fetchone()

    if not item:
        cur.close()
        conn.close()
        return "Cart item not found", 404

    if action == "remove" or (action == "decrease" and item["quantity"] <= 1):
        cur.execute("DELETE FROM cart WHERE id = %s", (cart_id,))
    elif action == "decrease":
        cur.execute("UPDATE cart SET quantity = quantity - 1 WHERE id = %s", (cart_id,))
    elif action == "increase":
        if item["quantity"] >= item["stock"]:
            flash(f"You can only order maximum of {item['stock']} items of this product", "danger")
        else:
            cur.execute("UPDATE cart SET quantity = quantity + 1 WHERE id = %s", (cart_id,))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/cart")


@shop_bp.route("/clear-cart", methods=["POST"])
@login_required
def clear_cart():
    """Remove all items from the user's cart."""
    conn = get_db()
    cur = get_cursor(conn)
    cur.execute("DELETE FROM cart WHERE user_id = %s", (session["user_id"],))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/cart")


@shop_bp.route("/cart")
def view_cart():
    if "user_id" not in session:
        return redirect("/login")

    with get_db_cursor() as (conn, cur):
        cur.execute("""
            SELECT cart.id as cart_id, products.name, products.price, cart.quantity,
                   (products.price * cart.quantity) as total
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = %s
        """, (session["user_id"],))

        items = cur.fetchall()
        total = sum(float(item['total']) for item in items) if items else 0

    return render_template("dashboard/cart.html", items=items, total=total)


@shop_bp.route("/checkout-page")
@login_required
def checkout_page():
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            SELECT products.name, products.price, cart.quantity,
                   (products.price * cart.quantity) as total
            FROM cart
            JOIN products ON cart.product_id = products.id
            WHERE cart.user_id = %s
        """, (session["user_id"],))

        items = cur.fetchall()

        if not items:
            return redirect("/cart")

        cur.execute("""
        select distinct products.shop_id from cart join products
        on cart.product_id=products.id
        where cart.user_id=%s
        """,(session["user_id"],))
        shop_row = cur.fetchone()
        shop_id = shop_row["shop_id"] if shop_row else None

        payment = None
        if shop_id is not None:
            payment=get_payment_methods(shop_id)
            if not payment:
                create_payment_method(shop_id)
                payment=get_payment_methods(shop_id)

        total = sum(float(item['total']) for item in items)

    return render_template("store/checkout.html", items=items, total=total,payment=payment)




@shop_bp.route("/orders")
@login_required
def orders():
    """Shop owner view — shows orders placed at MY shop."""
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            SELECT orders.*, shops.shop_name
            FROM orders
            JOIN shops ON orders.shop_id = shops.id
            WHERE shops.user_id = %s
            ORDER BY orders.created_at DESC
        """, (session["user_id"],))

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
            order_dict['items'] = [dict(i) for i in items]
            order_dict['total'] = sum(float(i['price']) * i['quantity'] for i in items)
            orders_list.append(order_dict)

    return render_template("dashboard/orders.html", orders=orders_list, is_shop_owner=True)


@shop_bp.route("/product/<int:product_id>")
def view_product(product_id):
    """View individual product and its reviews."""
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            SELECT products.*, shops.shop_name, shops.slug as shop_slug, shops.logo_url, shops.banner_url,
                   COALESCE(AVG(reviews.rating), 0) as avg_rating,
                   COUNT(reviews.id) as review_count
            FROM products
            JOIN shops ON products.shop_id = shops.id
            LEFT JOIN reviews ON products.id = reviews.product_id
            WHERE products.id = %s
            GROUP BY products.id, shops.shop_name, shops.slug, shops.logo_url, shops.banner_url
        """, (product_id,))
        product = cur.fetchone()

        if not product:
            return "Product not found", 404

        # Fetch related products from the same shop
        cur.execute("""
            SELECT * FROM products
            WHERE shop_id = %s AND id != %s
            ORDER BY created_at DESC
            LIMIT 4
        """, (product['shop_id'], product_id))
        related_products = cur.fetchall()

        cur.execute("""
            SELECT reviews.*, users.name as user_name 
            FROM reviews
            JOIN users ON reviews.user_id = users.id
            WHERE reviews.product_id = %s
            ORDER BY reviews.created_at DESC
        """, (product_id,))
        reviews = cur.fetchall()

        # Check if user has purchased this product (to allow reviewing)
        can_review = False
        if "user_id" in session:
            cur.execute("""
                SELECT 1 FROM order_items
                JOIN orders ON order_items.order_id = orders.id
                WHERE orders.user_id = %s AND order_items.product_id = %s
                LIMIT 1
            """, (session["user_id"], product_id))
            if cur.fetchone():
                # Check if already reviewed
                cur.execute("SELECT 1 FROM reviews WHERE user_id = %s AND product_id = %s", (session["user_id"], product_id))
                if not cur.fetchone():
                    can_review = True

    return render_template("store/product_details.html", product=product, reviews=reviews, can_review=can_review, related_products=related_products)


@shop_bp.route("/product/<int:product_id>/review", methods=["POST"])
@login_required
def submit_review(product_id):
    """Submit a review for a product. Only allowed if user purchased it."""
    rating = request.form.get("rating")
    comment = request.form.get("comment", "").strip()

    if not rating:
        flash("Rating is required", "danger")
        return redirect(f"/product/{product_id}")

    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError()
    except ValueError:
        flash("Invalid rating", "danger")
        return redirect(f"/product/{product_id}")

    user_id = session["user_id"]

    try:
        with get_db_cursor() as (conn, cur):
            # Verify purchase
            cur.execute("""
                SELECT 1 FROM order_items
                JOIN orders ON order_items.order_id = orders.id
                WHERE orders.user_id = %s AND order_items.product_id = %s
                LIMIT 1
            """, (user_id, product_id))
            
            if not cur.fetchone():
                flash("You can only review products you have purchased.", "danger")
                return redirect(f"/product/{product_id}")

            cur.execute("""
                INSERT INTO reviews (product_id, user_id, rating, comment)
                VALUES (%s, %s, %s, %s)
            """, (product_id, user_id, rating, comment))
        flash("Review submitted successfully!", "success")
    except Exception as e:
        logger.error(f"Failed to submit review: {e}")
        flash("You have already reviewed this product.", "danger")

    return redirect(f"/product/{product_id}")

@shop_bp.route("/payment-settings", methods=["GET", "POST"])
@login_required
def payment_settings():
    with get_db_cursor() as (conn, cur):
        cur.execute("""
        select id from shops where user_id=%s
        """, (session['user_id'],))
        shop = cur.fetchone()

    if not shop:
        return "Shop not found", 404

    payment = get_payment_methods(shop['id'])
    if not payment:
        create_payment_method(shop['id'])
        payment = get_payment_methods(shop['id'])

    if request.method == "POST":
        razorpay_enabled = "razorpay_enabled" in request.form
        upi_enabled = "upi_enabled" in request.form
        phone_enabled = "phone_enabled" in request.form
        qr_enabled = "qr_enabled" in request.form
        cod_enabled = "cod_enabled" in request.form
        pickup_enabled = "pickup_enabled" in request.form

        upi_id = request.form.get("upi_id", "").strip()
        phone_number = request.form.get("phone_number", "").strip()

        if upi_enabled and not validate_upi(upi_id):
            flash("Invalid UPI ID format.", "danger")
            return render_template("payment_settings.html", payment=payment)

        if phone_enabled and not validate_phone(phone_number):
            flash("Invalid phone number format (must be 10-15 digits).", "danger")
            return render_template("payment_settings.html", payment=payment)

        qr_image_url = payment.get("qr_image_url") if payment else None

        if "qr" in request.files and request.files["qr"].filename != "":
            result = uploader.upload(request.files["qr"], folder="payment_qr")
            qr_image_url = result["secure_url"]

        update_payment_method(
            shop["id"],
            razorpay_enabled,
            upi_enabled,
            qr_enabled,
            phone_enabled,
            cod_enabled,
            pickup_enabled,
            upi_id,
            phone_number,
            qr_image_url
        )

        flash("Payment methods updated successfully!", "success")
        return redirect("/dashboard")
    
    return render_template("payment_settings.html", payment=payment)



@shop_bp.route("/dashboard/order/<int:order_id>")
@login_required
def order_details(order_id):
    with get_db_cursor() as (conn, cur):
        # Make sure seller owns this order
        cur.execute("""
            SELECT
                orders.*,
                shops.shop_name
            FROM orders
            JOIN shops
            ON orders.shop_id=shops.id
            WHERE
                orders.id=%s
            AND
                shops.user_id=%s
        """,(order_id,session["user_id"]))
        order = cur.fetchone()

        if not order:
            return "Order not found",404

        cur.execute("""
            SELECT
                order_items.quantity,
                order_items.price,
                products.name,
                products.image_url
            FROM order_items
            JOIN products
            ON order_items.product_id=products.id
            WHERE order_items.order_id=%s
        """,(order_id,))
        items = cur.fetchall()

    return render_template(
        "dashboard/order_details.html",
        order=order,
        items=items
    )


@shop_bp.route("/dashboard/order/<int:order_id>/status",methods=["POST"])
@login_required
def update_order_status_dashboard(order_id):
    status = request.form.get("status")

    with get_db_cursor() as (conn, cur):
        cur.execute("""
            UPDATE orders
            SET status=%s
            WHERE id=%s
            AND shop_id IN (
                SELECT id
                FROM shops
                WHERE user_id=%s
            )
        """,(status,order_id,session["user_id"]))

    return redirect(f"/dashboard/order/{order_id}")