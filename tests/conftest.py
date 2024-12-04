import pytest
import random
import os

from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.services.base import Base
from app.dependecies import get_db

# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, '.env'))

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_TEST_DATABASE = f'test_{os.getenv("DB_DATABASE")}'

SQLALCHEMY_DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_TEST_DATABASE}"
)

# Create the engine and session for the test database
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_database():
    engine_init = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres",
        echo=True,
    )
    with engine_init.connect() as connection:
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.execute(text(f"DROP DATABASE IF EXISTS {DB_TEST_DATABASE}"))
        connection.execute(text(f"CREATE DATABASE {DB_TEST_DATABASE}"))
        print(f"Database {DB_TEST_DATABASE} successfully created.")


def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
        print("Tables successfully created.")
    except Exception as e:
        print(f"Error occurred during table creation: {e}")

def drop_database():
    engine_init = create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/postgres",
        echo=True,
    )
    with engine_init.connect() as connection:
        connection = connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.execute(
            text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{DB_TEST_DATABASE}'
                  AND pid <> pg_backend_pid();
            """)
        )
        connection.execute(text(f"DROP DATABASE IF EXISTS {DB_TEST_DATABASE}"))
        print(f"Database {DB_TEST_DATABASE} successfully dropped.")

# Dependency override for the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Apply the override to the FastAPI app
app.dependency_overrides[get_db] = override_get_db

# Fixture for the test client
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="session", autouse=True)
def setup_and_cleanup():
    create_database()
    create_tables()
    yield
    drop_database()