import re

def validate_phone(phone):
    """Validate phone number format (10-15 digits, optionally starting with +)."""
    if not phone:
        return False
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone)
    return bool(re.match(r'^\+?[0-9]{10,15}$', phone_clean))

def validate_upi(upi_id):
    """Validate UPI ID format (username@bank)."""
    if not upi_id:
        return False
    return bool(re.match(r'^[\w\.\-]+@[\w\-]+$', upi_id))

def validate_price(price):
    """Validate product price (non-negative float)."""
    if price is None:
        return False
    try:
        val = float(price)
        return val >= 0
    except (ValueError, TypeError):
        return False

def validate_stock(stock):
    """Validate stock quantity (non-negative integer)."""
    if stock is None:
        return False
    try:
        val = int(stock)
        return val >= 0
    except (ValueError, TypeError):
        return False

def validate_shop_name(name):
    """Validate shop name (1-100 characters)."""
    if not name or not isinstance(name, str):
        return False
    name_stripped = name.strip()
    return 1 <= len(name_stripped) <= 100

def validate_product_name(name):
    """Validate product name (1-150 characters)."""
    if not name or not isinstance(name, str):
        return False
    name_stripped = name.strip()
    return 1 <= len(name_stripped) <= 150
