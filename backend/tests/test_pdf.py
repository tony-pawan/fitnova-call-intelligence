import pytest
from backend.app.database.database import engine
from backend.app.database.base import Base
from backend.app.database.session import SessionLocal
from backend.app.models.call import Call, CallStatus
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag, Severity
from backend.app.services.pdf_service import PDFService

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_pdf_generation(db_session):
    """
    Verifies that PDFService can generate both single call and cumulative reports as non-empty bytes.
    """
    # 1. Reset tables
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # 2. Add Mock Call data
    call = Call(
        id=999,
        original_filename="pdf_test_call.wav",
        stored_filename="pdf_test_call.wav",
        audio_path="./storage/audio/pdf_test_call.wav",
        mime_type="audio/wav",
        file_size_bytes=5000,
        duration_seconds=95.0,
        status=CallStatus.Completed,
        language="en"
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    # 3. Add Mock Analysis
    analysis = CallAnalysis(
        id=999,
        call_id=call.id,
        overall_score=78,
        summary="Test scorecard summary.",
        recommendation="Mock recommendations list."
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    # 4. Add Mock IssueTag
    issue = IssueTag(
        analysis_id=analysis.id,
        tag="Mock Violation",
        severity=Severity.High,
        timestamp=12.5,
        quote="Advisor didn't say compliance terms",
        reason="Missed standard disclosures"
    )
    db_session.add(issue)
    db_session.commit()

    # 5. Verify PDF generation
    single_pdf = PDFService.generate_single_call_pdf(db_session, call.id)
    assert single_pdf is not None
    assert len(single_pdf) > 0
    assert b"%PDF" in single_pdf[:10]  # Standard PDF file header

    cumulative_pdf = PDFService.generate_cumulative_pdf(db_session)
    assert cumulative_pdf is not None
    assert len(cumulative_pdf) > 0
    assert b"%PDF" in cumulative_pdf[:10]
