import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@localhost:5432/shop_platform")
