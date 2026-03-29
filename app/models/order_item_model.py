from app.utils.db import get_db

def create_order_item(order_id,product_id,quantity):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("INSERT INTO order_items (order_id,product_id,quantity) VALUES (%s,%s,%s) RETURNING id", (order_id,product_id,quantity))
    
    conn.commit()
    cur.close()
    conn.close()
    