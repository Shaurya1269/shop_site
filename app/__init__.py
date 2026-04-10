from flask import Flask
import os
from dotenv import load_dotenv


def create_app():
    app = Flask(__name__)

    # Load environment variables
    load_dotenv()
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key_change_me')

    # CLI command to initialize the database
    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables from schema.sql."""
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
        print("Database initialized!")

    # Blueprint registration
    from app.routes.shop_routes import shop_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.order_routes import order_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp)
    app.register_blueprint(order_bp)

    return app
