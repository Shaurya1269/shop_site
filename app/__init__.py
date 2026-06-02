from flask import Flask
import os
import secrets
import logging
from dotenv import load_dotenv


def create_app():
    app = Flask(__name__)

    # Load environment variables
    load_dotenv()

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

    # Enable structured logging
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)

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
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(product_bp)

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

    conn.commit()
    cur.close()
    conn.close()
