from flask import Flask


def create_app():
    app = Flask(__name__)

    # config
    import os
    from dotenv import load_dotenv
    load_dotenv()
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key')

    # db init

    # blueprint registration
    from app.routes.shop_routes import shop_bp
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp)

    return app
