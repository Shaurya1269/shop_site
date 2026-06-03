from app.utils.db import get_db, get_cursor


def create_product(shop_id, name, price, description):
    """Create a new product in a shop."""
    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        INSERT INTO products (shop_id, name, price, description)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (shop_id, name, price, description))

    product_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    return {'id': product_id}


def get_product_by_id(product_id):
    conn = get_db()
    cur = get_cursor(conn)
    cur.execute("""
        SELECT * FROM products WHERE id = %s
    """, (product_id,))
    product = cur.fetchone()
    cur.close()
    conn.close()
    return product


def update_product(product_id, name, price, description, stock, image_url=None):
    conn = get_db()
    cur = get_cursor(conn)
    if image_url:
        cur.execute("""
            UPDATE products SET name = %s, price = %s, description = %s, stock = %s, image_url = %s WHERE id = %s
        """, (name, price, description, stock, image_url, product_id))
    else:
        cur.execute("""
            UPDATE products SET name = %s, price = %s, description = %s, stock = %s WHERE id = %s
        """, (name, price, description, stock, product_id))
    conn.commit()
    cur.close()
    conn.close()


def delete_product(product_id):
    conn = get_db()
    cur = get_cursor(conn)
    cur.execute("""
        DELETE FROM products WHERE id = %s
    """, (product_id,))
    conn.commit()
    cur.close()
    conn.close()

