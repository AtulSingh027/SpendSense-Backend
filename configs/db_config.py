import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Retrieve database credentials from environment variables
db_name = os.getenv("DATABASE_NAME", "spend_sense")
db_user = os.getenv("DATABASE_USER", "root")
db_password = os.getenv("DATABASE_PASSWORD", "12345")
db_host = os.getenv("DATABASE_HOST", "localhost")
db_port = os.getenv("DATABASE_PORT", "5432")

# Construct the PostgreSQL database URL using psycopg2
DATABASE_URL = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create the SQLAlchemy engine for PostgreSQL
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create a sessionmaker factory for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create the declarative Base class for models
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()