import os
from contextlib import contextmanager
from dotenv import load_dotenv
from psycopg2 import pool as pg_pool
import psycopg2

load_dotenv()

# A bounded connection pool, shared across all requests in this process,
# instead of opening a brand-new connection per request. minconn=2 keeps
# a couple of connections warm; maxconn=4 caps how many this single
# process instance will ever hold at once, leaving headroom for other
# things (other API replicas, psql sessions, etc.) sharing the same
# Postgres connection budget.
_pool = pg_pool.SimpleConnectionPool(
    minconn=2,
    maxconn=4,
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=os.getenv("DB_PORT", "5432"),
    dbname=os.getenv("DB_NAME", "minipay"),
    user=os.getenv("DB_USER", "minipay_app"),
    password=os.getenv("DB_PASSWORD"),
    connect_timeout=5,
)


@contextmanager
def get_connection():
    conn = _pool.getconn()

    # A connection can go stale if Postgres restarts while we're holding
    # it open in the pool. Detect that before handing it to a caller,
    # rather than recycling a dead connection over and over.
    if conn.closed:
        _pool.putconn(conn, close=True)
        conn = _pool.getconn()

    broken = False
    try:
        yield conn
    except psycopg2.OperationalError:
        broken = True
        raise
    finally:
        if broken or conn.closed:
            _pool.putconn(conn, close=True)
        else:
            _pool.putconn(conn)
