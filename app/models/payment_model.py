from app.utils.db import get_db,get_cursor

def get_payment_methods(shop_id):
    conn=get_db()
    cur=get_cursor(conn)

    cur.execute("""
    select * from payment_methods where shop_id=%s
    """,(shop_id,))
    payment=cur.fetchone()
    cur.close()
    conn.close()
    return payment 

def create_payment_method(shop_id):
    conn=get_db()
    cur=get_cursor(conn)
    cur.execute("""
    insert into payment_methods(shop_id) values(%s)
    """,(shop_id,))
    conn.commit()
    cur.close()
    conn.close()
    return True

def update_payment_method(shop_id,
        razorpay_enabled,
        upi_enabled,
        qr_enabled,
        phone_enabled,
        cod_enabled,
        pickup_enabled,
        upi_id,
        phone_number,
        qr_image_url):
        
        conn=get_db()
        cur=get_cursor(conn)
        
        cur.execute("""
        UPDATE payment_methods
        SET
            razorpay_enabled=%s,
            upi_enabled=%s,
            qr_enabled=%s,
            phone_enabled=%s,
            cod_enabled=%s,
            pickup_enabled=%s,
            upi_id=%s,
            phone_number=%s,
            qr_image_url=%s,
            updated_at=NOW()
        WHERE shop_id=%s
    """,
    (
        razorpay_enabled,
        upi_enabled,
        qr_enabled,
        phone_enabled,
        cod_enabled,
        pickup_enabled,
        upi_id,
        phone_number,
        qr_image_url,
        shop_id
    ))

        conn.commit()

        cur.close() 
        conn.close()
        return True

    