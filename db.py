import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "zepto_SQL_Analysis"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "4518"),
        port=os.getenv("DB_PORT", "5432")
    )

    return conn