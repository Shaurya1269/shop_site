from flask import Flask
import os
import logging
from dotenv import load_dotenv


def create_app():
    app = Flask(__name__)

    # Load environment variables
    load_dotenv()
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key_change_me')

    # Enable logging so errors show in Render logs
    if not app.debug:
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
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp)
    app.register_blueprint(order_bp)

    return app


def _init_db(app):
    """Auto-create tables on app startup if they don't exist."""
    try:
        _run_schema()
        app.logger.info("Database tables verified/created successfully.")
    except Exception as e:
        app.logger.error(f"Failed to initialize database: {e}")
        # Don't crash the app — let it start so we can see the error in logs


def _run_schema():
    """Execute schema.sql to create tables (IF NOT EXISTS makes this safe)."""
    from app.utils.db import get_db, get_cursor

    schema_path = os.path.join(os.path.dirname(
        __file__), '..', 'database', 'schema.sql')

    with open(schema_path, 'r') as f:
        schema = f.read()

    conn = get_db()
    cur = get_cursor(conn)
    cur.execute(schema)
    conn.commit()
    cur.close()
    conn.close()
