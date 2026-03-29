from app.routes.shop_routes import shop_bp
from app.routes.auth_routes import auth_bp
from flask import Flask
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def create_app():
    app = Flask(__name__)  # Create a new Flask application instance
    # Set a secret key for session management and security purposes
    app.secret_key = os.getenv('SECRET_KEY', 'fallback_secret_key')
    # Register the authentication blueprint with a URL prefix of '/auth'
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(shop_bp)
    return app  # Return the created Flask application instance
