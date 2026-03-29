from app.utils.db import get_db

def create_user(name,email,password_hash):
    conn= get_db()
    cur = conn.cursor()   # Create a cursor object to execute SQL queries
    
    cur.execute("""
        INSERT INTO users (name, email, password_hash)
        VALUES (%s, %s, %s)
        RETURNING id, name, email, created_at
    """, (name, email, password_hash))     # Execute the SQL query to insert a new user and return the inserted user's details
    
    user = cur.fetchone()   # Fetch the inserted user's details
    conn.commit()  # Commit the transaction to save changes to the database
    cur.close()   # Close the cursor
    conn.close()  # Close the database connection

    return user

def get_user_by_email(email):
    conn = get_db()
    cur= conn.cursor()   # Create a cursor object to execute SQL queries
    
    cur.execute("""SELECT id, name, email, password_hash
        FROM users
        WHERE email = %s
    """, (email,))
    
    user=cur.fetchone()
    
    cur.close()
    conn.close()
    return user

