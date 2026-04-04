from flask import Blueprint, render_template, session, redirect, request
from app.models.shop_model import create_shop
from app.models.product_model import create_product
from app.utils.db import get_db
from app.utils.decorators import login_required

shop_bp = Blueprint('shop', __name__)


@shop_bp.route("/")
def home():
    return render_template("index.html")


@shop_bp.route('/login')
def login_page():
    return render_template('auth/login.html')


@shop_bp.route('/register')
def register_page():
    return render_template('auth/register.html')


@shop_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard/dashboard.html')


@shop_bp.route('/create-shop', methods=['GET', 'POST'])
def create_shop_page():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        shop_name = request.form.get("shop_name")
        shop = create_shop(session['user_id'], shop_name)
        return redirect("/dashboard")

    return render_template("dashboard/create_shop.html")


@shop_bp.route("/shop/<slug>")
def public_store(slug):
    conn = get_db()
    cur = conn.cursor()

    # Get shop
    cur.execute("SELECT * FROM shops WHERE slug = ?", (slug,))
    shop = cur.fetchone()

    if not shop:
        cur.close()
        conn.close()
        return "Shop not found", 404

    # Get products for this shop
    cur.execute("SELECT * FROM products WHERE shop_id = ?", (shop['id'],))
    products = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("store/store.html", shop=shop, products=products)


@shop_bp.route("/add-product", methods=["GET", "POST"])
def add_product():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        name = request.form.get("name")
        price = request.form.get("price")
        description = request.form.get("description")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM shops WHERE user_id = ?",
                    (session["user_id"],))
        shop = cur.fetchone()
        cur.close()
        conn.close()

        if not shop:
            return "No shop found"

        create_product(shop['id'], name, price, description)
        return redirect('/dashboard')

    return render_template("dashboard/add_product.html")


@shop_bp.route("/add-to-cart", methods=["POST"])
def add_to_cart():
    if "user_id" not in session:
        return redirect("/login")

    product_id = request.form.get("product_id")

    conn = get_db()
    cur = conn.cursor()

    # check existing cart shop
    cur.execute("""
    SELECT products.shop_id
    FROM cart
    JOIN products ON cart.product_id = products.id
    WHERE cart.user_id = ?
    LIMIT 1
""", (session["user_id"],))

    existing = cur.fetchone()

# get new product shop
    cur.execute(
        "SELECT shop_id FROM products WHERE id = ?",
        (product_id,)
    )
    new_product = cur.fetchone()

    if existing and existing["shop_id"] != new_product["shop_id"]:
        return "You can only order from one shop at a time", 400


@shop_bp.route("/cart")
def view_cart():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT products.name, products.price, cart.quantity,
               (products.price * cart.quantity) as total
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
    """, (session["user_id"],))

    items = cur.fetchall()

    # Calculate grand total
    total = sum(item['total'] for item in items) if items else 0

    cur.close()
    conn.close()

    return render_template("cart.html", items=items, total=total)


@shop_bp.route("/checkout-page")
@login_required
def checkout_page():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT products.name, products.price, cart.quantity,
               (products.price * cart.quantity) as total
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
    """, (session["user_id"],))

    items = cur.fetchall()

    if not items:
        cur.close()
        conn.close()
        return redirect("/cart")

    # Calculate grand total
    total = sum(item['total'] for item in items)

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
    cur = conn.cursor()

    # Get all cart items for user
    cur.execute("""
        SELECT cart.id, products.id as product_id, products.price, cart.quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id = ?
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
                       item['quantity'], item['price'])

    # Clear cart
    cur.execute("DELETE FROM cart WHERE user_id = ?", (session["user_id"],))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/orders")


@shop_bp.route("/orders")
@login_required
def orders():
    conn = get_db()
    cur = conn.cursor()

    # Get orders with shop information
    cur.execute("""
        SELECT orders.*, shops.shop_name
        FROM orders
        JOIN shops ON orders.shop_id = shops.id
        WHERE orders.id IN (
            SELECT DISTINCT order_id FROM order_items
            WHERE product_id IN (
                SELECT id FROM products WHERE shop_id IN (
                    SELECT id FROM shops WHERE user_id = ?
                )
            )
        )
        ORDER BY orders.created_at DESC
    """, (session["user_id"],))

    orders_data = cur.fetchall()

    # Get order items for each order
    orders = []
    for order in orders_data:
        cur.execute("""
            SELECT order_items.*, products.name as product_name
            FROM order_items
            JOIN products ON order_items.product_id = products.id
            WHERE order_items.order_id = ?
        """, (order['id'],))

        items = cur.fetchall()
        order_dict = dict(order)
        order_dict['items'] = items
        orders.append(order_dict)

    cur.close()
    conn.close()

    return render_template("dashboard/orders.html", orders=orders)
