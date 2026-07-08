import os
from backend.app.core.logging import get_logger, setup_logging
from backend.app.database.database import engine
from backend.app.database.base import Base

# Import models to register them on Base.metadata
from backend.app.models.call import Call
from backend.app.models.analysis import CallAnalysis
from backend.app.models.transcript import TranscriptSegment
from backend.app.models.issue_tag import IssueTag
from backend.app.models.version_models import TranscriptVersion, ConversationVersion, AnalysisVersion
from backend.app.models.organization import Organization
from backend.app.models.team import Team
from backend.app.models.advisor import Advisor
from backend.app.models.ingestion_source import IngestionSource
from sqlalchemy import text  # pyrefly: ignore [missing-import]

logger = get_logger("DATABASE")

def init_db() -> None:
    """
    Initializes database schema. Creates tables if they do not exist.
    """
    logger.info("Initializing database...")
    try:
        # Create any missing tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database base tables verified/created.")
        
        # Use SQLAlchemy inspector to check table columns before applying migrations
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        call_cols = [col["name"] for col in inspector.get_columns("calls")]
        tag_cols = [col["name"] for col in inspector.get_columns("issue_tags")]
        
        # Run schema migrations dynamically to prevent column mismatch errors on existing installations
        with engine.begin() as conn:
            # 1. Update 'calls' table
            if "source" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN source VARCHAR(100) DEFAULT 'Upload';"))
            if "vendor" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN vendor VARCHAR(100) DEFAULT 'Direct';"))
            if "external_call_id" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN external_call_id VARCHAR(255);"))
            if "customer_name" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN customer_name VARCHAR(255);"))
            if "advisor_name" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN advisor_name VARCHAR(255);"))
            if "ingestion_metadata" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN ingestion_metadata TEXT;"))
            
            # New Org data hierarchy migration columns
            if "organization_id" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL;"))
            if "team_id" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN team_id INTEGER REFERENCES teams(id) ON DELETE SET NULL;"))
            if "advisor_id" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN advisor_id INTEGER REFERENCES advisors(id) ON DELETE SET NULL;"))
            if "source_id" not in call_cols:
                conn.execute(text("ALTER TABLE calls ADD COLUMN source_id INTEGER REFERENCES ingestion_sources(id) ON DELETE SET NULL;"))
            
            # 2. Update 'issue_tags' table
            if "review_status" not in tag_cols:
                conn.execute(text("ALTER TABLE issue_tags ADD COLUMN review_status VARCHAR(100) DEFAULT 'Pending';"))
            if "reviewer_comments" not in tag_cols:
                conn.execute(text("ALTER TABLE issue_tags ADD COLUMN reviewer_comments TEXT;"))
            if "confidence" not in tag_cols:
                conn.execute(text("ALTER TABLE issue_tags ADD COLUMN confidence FLOAT;"))
            if "recommendation" not in tag_cols:
                conn.execute(text("ALTER TABLE issue_tags ADD COLUMN recommendation TEXT;"))
            if "evidence_segments" not in tag_cols:
                conn.execute(text("ALTER TABLE issue_tags ADD COLUMN evidence_segments TEXT;"))
            
        logger.info("Database schema upgrades completed successfully. Triggering data seed...")
        
        from backend.app.database.session import SessionLocal
        from backend.app.services.org_team_advisor_service import OrgTeamAdvisorService
        db = SessionLocal()
        try:
            OrgTeamAdvisorService.seed_initial_org_data(db)
            logger.info("Database baseline seed complete.")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error initializing or upgrading database schemas: {e}")
        raise

def main() -> None:
    setup_logging("INFO")
    init_db()

if __name__ == "__main__":
    main()
