from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import os
from dotenv import load_dotenv
from src.models.job import Base

load_dotenv()

def get_database_url():
    """Get database URL from environment variables."""
    return os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/geodata")

def init_db():
    """Initialize database connection and create tables."""
    db_url = get_database_url()
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine

def get_session():
    """Create a new database session."""
    engine = init_db()
    Session = sessionmaker(bind=engine)
    return Session()

class DatabaseSession:
    """Context manager for database sessions."""
    def __enter__(self):
        self.session = get_session()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None:
                self.session.rollback()
            else:
                self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e
        finally:
            self.session.close()