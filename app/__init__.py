from flask import Flask
import os
import psycopg2
from dotenv import load_dotenv


def create_app():
    app = Flask(__name__)

    # config
    load_dotenv()
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key')

    @app.route("/init-db")
    def init_db():
        schema_path = os.path.join(os.path.dirname(
            __file__), '..', 'database', 'schema.sql')
        db_path = os.path.join(os.path.dirname(__file__), '..', 'shop.db')
        with open(schema_path, 'r') as f:
            schema = f.read()
        conn = psycopg2.connect(os.getenv("postgresql://shaurya:WO9M0uxXeskbGy3Lm8RmgbrPNMycN749@dpg-d74e8h450q8c73duv8ig-a.oregon-postgres.render.com/shopplatform123"))
        conn.executescript(schema)
        conn.commit()
        conn.close()
        return "Database initialized!!"

    # blueprint registration
    from app.routes.shop_routes import shop_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.order_routes import order_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp)
    app.register_blueprint(order_bp)

    return app
