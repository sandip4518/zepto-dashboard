import os
import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

# ── Connection Pool (reuses connections, avoids repeated SSL handshakes) ──
_pool = None


def _get_pool():
    """Lazy-init a connection pool (min 1, max 5 connections)."""
    global _pool
    if _pool is None or _pool.closed:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            _pool = psycopg2.pool.SimpleConnectionPool(
                1, 5, dsn=db_url, sslmode=os.getenv("DB_SSLMODE", "require")
            )
        else:
            host = os.getenv("DB_HOST")
            db_name = os.getenv("DB_NAME")
            user = os.getenv("DB_USER")
            password = os.getenv("DB_PASS")
            port = os.getenv("DB_PORT", "5432")

            if not all([host, db_name, user, password]):
                raise RuntimeError(
                    "No DATABASE_URL or DB_HOST/DB_NAME/DB_USER/DB_PASS found in .env. "
                    "Please configure your database credentials."
                )

            _pool = psycopg2.pool.SimpleConnectionPool(
                1, 5,
                host=host,
                database=db_name,
                user=user,
                password=password,
                port=port,
            )
    return _pool


def get_db_connection():
    """Get a connection from the pool."""
    return _get_pool().getconn()


def release_db_connection(conn):
    """Return a connection to the pool."""
    try:
        _get_pool().putconn(conn)
    except Exception:
        pass