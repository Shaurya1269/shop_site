from app.utils.db import get_db


def create_order_item(order_id, product_id, quantity):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("INSERT INTO order_items (order_id,product_id,quantity) VALUES (?,?,?)",
                (order_id, product_id, quantity))

    item_id = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()

    return item_id
