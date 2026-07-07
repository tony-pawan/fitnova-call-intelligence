from sqlalchemy import create_engine  # pyrefly: ignore [missing-import]
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger("DATABASE")

logger.info("Initializing SQLAlchemy database engine...")

# SQLAlchemy engine configured for PostgreSQL.
# pool_pre_ping=True enables checking connection health on checkout.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=False
)
