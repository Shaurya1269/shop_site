from flask import Flask
import os
import secrets
import logging
from dotenv import load_dotenv
import cloudinary


def create_app():
    app = Flask(__name__)

    # Load environment variables
    load_dotenv()

    cloudinary.config(
        cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
        api_key=os.environ.get("CLOUDINARY_API_KEY"),
        api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
        secure=True
    )

    # Use SECRET_KEY from env; fall back to a random key (invalidates sessions on restart)
    # For persistent sessions across restarts, always set SECRET_KEY in .env
    secret = os.getenv('SECRET_KEY')
    if not secret:
        app.logger.warning(
            "SECRET_KEY not set in environment. Generating a random key. "
            "Sessions will be lost on restart. Set SECRET_KEY in .env for production."
        )
        secret = secrets.token_hex(32)
    app.secret_key = secret

    # Session Cookie Security
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    env_debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
    app.config["SESSION_COOKIE_SECURE"] = not env_debug

    # CSRF Protection — shared instance from app.extensions
    from app.extensions import csrf
    csrf.init_app(app)

    # Enable structured logging
    from logging.handlers import RotatingFileHandler
    if not os.path.exists("logs"):
        os.makedirs("logs")
    file_handler = RotatingFileHandler("logs/app.log", maxBytes=5*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] - %(message)s')
    file_handler.setFormatter(formatter)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.INFO)

    # Auto-create database tables on startup
    _init_db(app)

    # CLI command to initialize the database (manual trigger)
    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables from schema.sql."""
        _run_schema()
        print("Database initialized!")

    # Blueprint registration
    from app.routes.shop_routes import shop_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.order_routes import order_bp
    from app.routes.product_routes import product_bp
    from app.routes.payment_routes import payment_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(product_bp)
    app.register_blueprint(payment_bp)

    return app


def _init_db(app):
    """Auto-create tables and run migrations on app startup."""
    try:
        _run_schema()
        app.logger.info("Database tables verified/created successfully.")
    except Exception as e:
        app.logger.error(f"Failed to initialize database: {e}")
        # Don't crash the app — let it start so we can see the error in logs


def _run_schema():
    """Execute schema.sql to create tables and run all migrations."""
    from app.utils.db import get_db, get_cursor

    schema_path = os.path.join(os.path.dirname(
        __file__), '..', 'database', 'schema.sql')

    with open(schema_path, 'r') as f:
        schema = f.read()

    conn = get_db()
    cur  = get_cursor(conn)

    # ── Base schema ────────────────────────────────────────────────
    cur.execute(schema)

    # ── Migration 1: ensure user_id column exists on orders ───────
    # The original schema omitted user_id; this migration is idempotent.
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'orders' AND column_name = 'user_id'
            ) THEN
                ALTER TABLE orders
                    ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # migration 2: ensure status column exists or orders
    cur.execute("""
    Do $$
    begin
    if not exists(
    select 1 from information_schema.columns
    where table_name='orders' and column_name='status')
    then
    alter table orders add column status varchar(20) default 'pending';
    end if;
    end $$; """)

    # migration 3: ensure payment_method and payment_status columns exist
    cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'orders' AND column_name = 'payment_method'
        ) THEN
            ALTER TABLE orders ADD COLUMN payment_method TEXT;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'orders' AND column_name = 'payment_status'
        ) THEN
            ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'Pending';
        END IF;
    END $$;
    """)

    cur.execute("""
    do $$
    begin

    if not exists(
    select 1
    from information_schema.columns
    where table_name='shops'
    and column_name='description'
    )then   
    alter table shops
    add column description text;
    end if;

    if not exists(
    select 1
    from information_schema.columns
    where table_name='shops'
    and column_name='category'
    )then   
    alter table shops
    add column category text;
    end if;

    if not exists(
    select 1
    from information_schema.columns
    where table_name='shops'
    and column_name='logo_url'
    )then
    alter table shops
    add column logo_url text;
    end if;

    if not exists(
    select 1
    from information_schema.columns
    where table_name='shops'
    and column_name='banner_url'
    )then
    alter table shops
    add column banner_url text;
    end if;
end $$;
    """)


    # ── Migration 4: Razorpay tracking columns + payment_time ───────────────
    cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'orders' AND column_name = 'razorpay_order_id'
        ) THEN
            ALTER TABLE orders ADD COLUMN razorpay_order_id TEXT;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'orders' AND column_name = 'razorpay_payment_id'
        ) THEN
            ALTER TABLE orders ADD COLUMN razorpay_payment_id TEXT;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'orders' AND column_name = 'payment_time'
        ) THEN
            ALTER TABLE orders ADD COLUMN payment_time TIMESTAMP;
        END IF;
    END $$;
    """)

    # ── Migration 5: Shop-specific Razorpay credentials columns ──────────────
    cur.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'payment_methods' AND column_name = 'razorpay_key_id'
        ) THEN
            ALTER TABLE payment_methods ADD COLUMN razorpay_key_id TEXT;
        END IF;
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'payment_methods' AND column_name = 'razorpay_key_secret'
        ) THEN
            ALTER TABLE payment_methods ADD COLUMN razorpay_key_secret TEXT;
        END IF;
    END $$;
    """)

    conn.commit()
    cur.close()
    conn.close()
