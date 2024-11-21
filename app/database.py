import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import sqlite3
import datetime


def register_sqlite_adapters():
    """Register custom adapters and converters for SQLite."""

    def adapt_date_iso(val):
        """Adapt datetime.date to ISO 8601 date."""
        return val.isoformat()

    def adapt_datetime_iso(val):
        """Adapt datetime.datetime to timezone-naive ISO 8601 date."""
        return val.isoformat()

    def adapt_datetime_epoch(val):
        """Adapt datetime.datetime to Unix timestamp."""
        return int(val.timestamp())

    sqlite3.register_adapter(datetime.date, adapt_date_iso)
    sqlite3.register_adapter(datetime.datetime, adapt_datetime_iso)
    sqlite3.register_adapter(datetime.datetime, adapt_datetime_epoch)

    def convert_date(val):
        """Convert ISO 8601 date to datetime.date object."""
        return datetime.date.fromisoformat(val.decode())

    def convert_datetime(val):
        """Convert ISO 8601 datetime to datetime.datetime object."""
        return datetime.datetime.fromisoformat(val.decode())

    def convert_timestamp(val):
        """Convert Unix epoch timestamp to datetime.datetime object."""
        return datetime.datetime.fromtimestamp(int(val))

    sqlite3.register_converter("date", convert_date)
    sqlite3.register_converter("datetime", convert_datetime)
    sqlite3.register_converter("timestamp", convert_timestamp)


register_sqlite_adapters()

# Define the SQLite URL for synchronous access
DATABASE_URL = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'db', 'library.db')}"

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=True)

# Create a sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Define a base class for declarative models
Base = declarative_base()


# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
