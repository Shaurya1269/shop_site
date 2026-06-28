from app.utils.db import get_db_cursor

def get_payment_methods(shop_id):
    with get_db_cursor() as (conn, cur):
        cur.execute("""
        select * from payment_methods where shop_id=%s
        """,(shop_id,))
        payment=cur.fetchone()
    return payment 

def create_payment_method(shop_id):
    with get_db_cursor() as (conn, cur):
        cur.execute("""
        insert into payment_methods(shop_id) values(%s)
        """,(shop_id,))
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
        qr_image_url,
        razorpay_key_id=None,
        razorpay_key_secret=None):
        
        with get_db_cursor() as (conn, cur):
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
                razorpay_key_id=%s,
                razorpay_key_secret=%s,
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
            razorpay_key_id,
            razorpay_key_secret,
            shop_id
        ))

        return True


    