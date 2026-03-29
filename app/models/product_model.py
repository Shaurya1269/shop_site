from app.utils.db import get_db

def create_product(shop_id, name, price, description):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products (shop_id, name, price, description)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (shop_id, name, price, description))

    product = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return product