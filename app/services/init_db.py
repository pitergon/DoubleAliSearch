import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from app.services.base import Base
from app.models.user import User
from app.models.search import Search


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_DATABASE = os.getenv("DB_DATABASE")

def create_database():
    engine_init = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres",
        echo=True,
    )
    with engine_init.connect() as connection:
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        result = connection.execute(
            text(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_DATABASE}'")
        )
        if result.fetchone():
            print(f"Database {DB_DATABASE} already exists.")
        else:
            connection.execute(text(f"CREATE DATABASE {DB_DATABASE}"))
            print(f"Database {DB_DATABASE} successfully created.")


def create_tables():

    engine = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}",
        echo=True,
    )
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables successfully created.")
    except Exception as e:
        print(f"Error occurred during table creation: {e}")


if __name__ == "__main__":
    create_database()
    create_tables()
