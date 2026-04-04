from app.utils.db import get_db


def create_product(shop_id, name, price, description):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO products (shop_id, name, price, description)
        VALUES (?, ?, ?, ?)
        """,
                (shop_id, name, price, description))

    product_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()

    return {'id': product_id}
