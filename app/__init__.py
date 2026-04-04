from flask import Flask
from app.extensions import db


def create_app():
    app = Flask(__name__)

    # config
    import os
    from dotenv import load_dotenv
    load_dotenv()
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 'sqlite:///shop.db')

    # db init
    db.init_app(app)
    
    
    @app.route("/init-db")
    def init_db():
        import app.models.user_model
        import app.models.product_model
        import app.models.shop_model
        db.create_all()
        return "Database intialized!!"
    
    # blueprint registration
    from app.routes.shop_routes import shop_bp
    from app.routes.auth_routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp)

    return app
