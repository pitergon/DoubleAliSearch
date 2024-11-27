import os
import psycopg2
from psycopg2.extensions import connection


def get_db_connection() -> connection:
    """Connect to the database PostgreSQL"""
    conn = psycopg2.connect(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        database=os.getenv('DB_DATABASE')
    )
    return conn

