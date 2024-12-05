import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from app.services.base import Base
from app.models.models import User
from app.models.models import Search


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")


def create_database():
    engine_init = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres",
        echo=True,
    )
    with engine_init.connect() as connection:
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        result = connection.execute(
            text(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        )
        if result.fetchone():
            print(f"Database {DB_NAME} already exists.")
        else:
            connection.execute(text(f"CREATE DATABASE {DB_NAME}"))
            print(f"Database {DB_NAME} successfully created.")


def create_tables():

    engine = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
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
