from app.utils.db import get_db_cursor


def create_product(shop_id, name, price, description):
    """Create a new product in a shop."""
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            INSERT INTO products (shop_id, name, price, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (shop_id, name, price, description))
        product_id = cur.fetchone()['id']

    return {'id': product_id}


def get_product_by_id(product_id):
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            SELECT * FROM products WHERE id = %s
        """, (product_id,))
        product = cur.fetchone()
    return product


def update_product(product_id, name, price, description, stock, image_url=None):
    with get_db_cursor() as (conn, cur):
        if image_url:
            cur.execute("""
                UPDATE products SET name = %s, price = %s, description = %s, stock = %s, image_url = %s WHERE id = %s
            """, (name, price, description, stock, image_url, product_id))
        else:
            cur.execute("""
                UPDATE products SET name = %s, price = %s, description = %s, stock = %s WHERE id = %s
            """, (name, price, description, stock, product_id))


def delete_product(product_id):
    with get_db_cursor() as (conn, cur):
        cur.execute("""
            DELETE FROM products WHERE id = %s
        """, (product_id,))


