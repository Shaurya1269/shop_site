from flask import Blueprint, render_template, session, redirect, request, flash
from app.models.shop_model import create_shop
from app.models.product_model import create_product
from app.utils.db import get_db, get_cursor
from app.utils.decorators import login_required
import os

shop_bp = Blueprint('shop', __name__)


@shop_bp.route("/")
def home():
    conn=get_db()
    cur=conn.cursor()
    
    cur.execute("select shop_name,slug from shops")
    shops=cur.fetchall()
    
    cur.close()
    conn.close()
    return render_template("home.html", shops=shops)


@shop_bp.route("/health")
def health():
    """Diagnostic route to test database connection."""
    try:
        conn = get_db()
        cur = get_cursor(conn)
        cur.execute("SELECT 1")
        cur.close()

        # Check if tables exist
        cur = get_cursor(conn)
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row['table_name'] for row in cur.fetchall()]
        cur.close()
        conn.close()

        return {
            "status": "ok",
            "database": "connected",
            "tables": tables,
            "DATABASE_URL_set": bool(os.getenv("DATABASE_URL"))
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
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
    conn = get_db()
    cur = get_cursor(conn)

    # Get the user's shop if they have one
    cur.execute("SELECT * FROM shops WHERE user_id = %s", (session['user_id'],))
    shop = cur.fetchone()

    # Get products if shop exists
    products = []
    if shop:
        cur.execute("SELECT * FROM products WHERE shop_id = %s", (shop['id'],))
        products = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('dashboard/dashboard.html', shop=shop, products=products)


@shop_bp.route('/create-shop', methods=['GET', 'POST'])
@login_required
def create_shop_page():
    if request.method == 'POST':
        shop_name = request.form.get("shop_name")
        if not shop_name:
            return "Shop name is required", 400
        shop = create_shop(session['user_id'], shop_name)
        return redirect("/dashboard")

    return render_template("dashboard/create_shop.html")


@shop_bp.route("/shop/<slug>")
def view_store(slug):
    """Public store page — anyone can view a shop by its slug."""
    conn = get_db()
    cur = get_cursor(conn)

    # Get shop by slug from the shops table
    cur.execute("SELECT id, shop_name, slug FROM shops WHERE slug = %s", (slug,))
    shop = cur.fetchone()

    if not shop:
        cur.close()
        conn.close()
        return "Shop not found", 404

    # Get products for this shop
    cur.execute(
        "SELECT id, name, price, description FROM products WHERE shop_id = %s",
        (shop['id'],)
    )
    products = cur.fetchall()

    cur.close()
    conn.close()
    return render_template("store/store.html", shop=shop, products=products)


@shop_bp.route("/add-product", methods=["GET", "POST"])
@login_required
def add_product():
    user_id = session.get("user_id")

    conn = get_db()
    cur = get_cursor(conn)
    cur.execute("SELECT id FROM shops WHERE user_id = %s", (user_id,))
    shop = cur.fetchone()

    if not shop:
        cur.close()
        conn.close()
        return "Create a shop first", 400

    shop_id = shop['id']

    if request.method == 'POST':
        name = request.form.get("name")
        price = request.form.get('price')
        description = request.form.get('description')

        if not name or not price:
            cur.close()
            conn.close()
            return "Name and price are required", 400

        try:
            price = float(price)
        except ValueError:
            cur.close()
            conn.close()
            return "Price must be a number", 400

        cur.execute(
            """INSERT INTO products (shop_id, name, price, description)
               VALUES (%s, %s, %s, %s)""",
            (shop_id, name, price, description)
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/dashboard")

    cur.close()
    conn.close()
    return render_template("dashboard/add_product.html")


@shop_bp.route("/add-to-cart", methods=["POST"])
@shop_bp.route("/add-to-cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id=None):
    """Add a product to the user's cart. Accepts product_id from form data or URL."""
    if "user_id" not in session:
        return redirect("/login")

    # Accept product_id from URL path or form body
    if product_id is None:
        product_id = request.form.get("product_id")

    if not product_id:
        return "Product ID is required", 400

    # Convert to int for safety
    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return "Invalid product ID", 400

    conn = get_db()
    cur = get_cursor(conn)

    # Verify the product exists and get its shop
    cur.execute("SELECT id, shop_id FROM products WHERE id = %s", (product_id,))
    new_product = cur.fetchone()

    if not new_product:
        cur.close()
        conn.close()
        return "Product not found", 404

    # Check if cart already has items from a different shop
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

    # Check if product already in cart — increment quantity
    cur.execute("""
        SELECT id, quantity FROM cart
        WHERE user_id = %s AND product_id = %s
    """, (session["user_id"], product_id))
    existing_item = cur.fetchone()

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

    return redirect(request.referrer or "/")


@shop_bp.route("/update-cart", methods=["POST"])
@login_required
def update_cart():
    """Update quantity of a cart item or remove it."""
    cart_id = request.form.get("cart_id")
    action = request.form.get("action")  # "increase", "decrease", or "remove"

    if not cart_id or not action:
        return "Missing parameters", 400

    conn = get_db()
    cur = get_cursor(conn)

    # Verify cart item belongs to user
    cur.execute("SELECT id, quantity FROM cart WHERE id = %s AND user_id = %s",
                (cart_id, session["user_id"]))
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

    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT cart.id as cart_id, products.name, products.price, cart.quantity,
               (products.price * cart.quantity) as total
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (session["user_id"],))

    items = cur.fetchall()

    # Calculate grand total
    total = sum(float(item['total']) for item in items) if items else 0

    cur.close()
    conn.close()

    return render_template("dashboard/cart.html", items=items, total=total)


@shop_bp.route("/checkout-page")
@login_required
def checkout_page():
    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT products.name, products.price, cart.quantity,
               (products.price * cart.quantity) as total
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (session["user_id"],))

    items = cur.fetchall()

    if not items:
        cur.close()
        conn.close()
        return redirect("/cart")

    # Calculate grand total
    total = sum(float(item['total']) for item in items)

    cur.close()
    conn.close()

    return render_template("store/checkout.html", items=items, total=total)


@shop_bp.route("/checkout", methods=["POST"])
@login_required
def checkout():
    from app.models.order_model import create_order, add_order_item, validate_cart_single_shop

    # Validate cart is from single shop
    shop_id, error = validate_cart_single_shop(session["user_id"])
    if error:
        return error, 400

    # Get customer details from form
    customer_name = request.form.get("customer_name")
    phone = request.form.get("phone")
    address = request.form.get("address")

    if not all([customer_name, phone, address]):
        return "All customer details required", 400

    conn = get_db()
    cur = get_cursor(conn)

    # Get all cart items for user
    cur.execute("""
        SELECT cart.id, products.id as product_id, products.price, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = %s
    """, (session["user_id"],))

    cart_items = cur.fetchall()

    if not cart_items:
        cur.close()
        conn.close()
        return "Cart is empty", 400

    # Create order
    order = create_order(session["user_id"], shop_id,
                         customer_name, phone, address)

    # Add items to order
    for item in cart_items:
        add_order_item(order['id'], item['product_id'],
                       item['quantity'], float(item['price']))

    # Clear cart
    cur.execute("DELETE FROM cart WHERE user_id = %s", (session["user_id"],))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/orders")


@shop_bp.route("/orders")
@login_required
def orders():
    conn = get_db()
    cur = get_cursor(conn)

    # Get orders for shops owned by this user
    cur.execute("""
        SELECT orders.*, shops.shop_name
        FROM orders
        JOIN shops ON orders.shop_id = shops.id
        WHERE shops.user_id = %s
        ORDER BY orders.created_at DESC
    """, (session["user_id"],))

    orders_data = cur.fetchall()

    # Get order items for each order
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

