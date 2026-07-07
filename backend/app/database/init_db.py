import os
from backend.app.core.logging import get_logger, setup_logging
from backend.app.database.database import engine
from backend.app.database.base import Base

# Import models to register them on Base.metadata
from backend.app.models.call import Call
from backend.app.models.analysis import CallAnalysis
from backend.app.models.transcript import TranscriptSegment
from backend.app.models.issue_tag import IssueTag

logger = get_logger("DATABASE")

def init_db() -> None:
    """
    Initializes database schema. Creates tables if they do not exist.
    """
    logger.info("Initializing database...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database schemas: {e}")
        raise

def main() -> None:
    setup_logging("INFO")
    init_db()

if __name__ == "__main__":
    main()
