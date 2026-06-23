from contextlib import contextmanager

@contextmanager
def get_db_cursor():
    conn=get_db()
    cur=conn.cursor()
    try:
        yield conn,cur
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
