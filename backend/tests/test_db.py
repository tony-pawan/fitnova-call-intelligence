from backend.app.database.session import SessionLocal
from backend.app.database.database import engine
from backend.app.database.base import Base
from backend.app.models.call import Call
from backend.app.models.analysis import CallAnalysis
from backend.app.models.transcript import TranscriptSegment
from backend.app.models.issue_tag import IssueTag

def test_db_empty_initial_state() -> None:
    """
    Verifies that the database is successfully connected and initializes in a clean,
    empty state (zero records exist).
    """
    # Drop and recreate tables to guarantee empty state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Check Call
        calls = db.query(Call).all()
        assert len(calls) == 0

        # Check CallAnalysis
        analyses = db.query(CallAnalysis).all()
        assert len(analyses) == 0

        # Check TranscriptSegment
        segments = db.query(TranscriptSegment).all()
        assert len(segments) == 0

        # Check IssueTag
        tags = db.query(IssueTag).all()
        assert len(tags) == 0
    finally:
        db.close()
