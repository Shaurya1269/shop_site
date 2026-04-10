from app.utils.db import get_db, get_cursor


def create_user(name, email, password_hash):
    """Create a new user and return their details."""
    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        INSERT INTO users (name, email, password_hash)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (name, email, password_hash))

    user_id = cur.fetchone()['id']
    conn.commit()
    cur.close()
    conn.close()

    return {'id': user_id, 'name': name, 'email': email}


def get_user_by_email(email):
    """Retrieve a user by their email address. Returns a dict or None."""
    conn = get_db()
    cur = get_cursor(conn)

    cur.execute("""
        SELECT id, name, email, password_hash
        FROM users
        WHERE email = %s
    """, (email,))

    user = cur.fetchone()

    cur.close()
    conn.close()
    return user
