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

    # Fallback: require individual DB_* env vars (no hardcoded defaults)
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

    return psycopg2.connect(
        host=host,
        database=db_name,
        user=user,
        password=password,
        port=port,
    )