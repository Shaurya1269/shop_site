import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database connection URL — set in .env or environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Flask secret key for session encryption
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_secret_key_change_me")
