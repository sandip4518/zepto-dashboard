import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """Return a psycopg2 connection.

    Preference order:
      1. `DATABASE_URL` (accepted by psycopg2) — use for Render/Neon.
      2. Individual `DB_*` vars for local development.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return psycopg2.connect(db_url, sslmode=os.getenv("DB_SSLMODE", "require"))

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "zepto_SQL_Analysis"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "4518"),
        port=os.getenv("DB_PORT", "5432"),
    )

    return conn