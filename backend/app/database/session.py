from typing import Generator
from sqlalchemy.orm import sessionmaker  # pyrefly: ignore [missing-import]
from backend.app.database.database import engine

# Configured sessionmaker for creating transactional scope database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

def get_db() -> Generator:
    """
    Dependency generator that creates a new SQLAlchemy session for each request
    and ensures it gets closed after the request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
