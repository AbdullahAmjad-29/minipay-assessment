import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """Open a direct database connection using env-based config.

    Raises psycopg2.OperationalError on connection failure - callers
    are expected to handle that explicitly, not let it crash silently.
    """
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "minipay"),
        user=os.getenv("DB_USER", "minipay_app"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
    )
