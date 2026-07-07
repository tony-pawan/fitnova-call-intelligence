import os
import pytest  # pyrefly: ignore [missing-import]
from backend.app.database.database import engine
from backend.app.database.base import Base
from backend.app.database.session import SessionLocal
from backend.app.models.call import Call, CallStatus
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag, Severity
from backend.app.services.dashboard_service import DashboardService

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_dashboard_service_empty_db(db_session) -> None:
    """
    Verifies that DashboardService returns safe default collections and counts
    when the database is completely empty.
    """
    # Reset database schema to guarantee empty state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    metrics = DashboardService.get_dashboard_metrics(db_session)
    assert metrics["total_calls"] == 0
    assert metrics["completed_calls"] == 0
    assert metrics["average_score"] == 0.0
    assert metrics["average_duration"] == 0.0

    trends = DashboardService.get_score_trends(db_session)
    assert len(trends) == 0

    issues = DashboardService.get_issue_distribution(db_session)
    assert len(issues["top_issues"]) == 0
    assert all(v == 0 for v in issues["severity_breakdown"].values())

    stats = DashboardService.get_processing_statistics(db_session)
    assert all(v == 0 for v in stats.values())

    history = DashboardService.get_history(db_session)
    assert len(history) == 0

def test_dashboard_service_aggregation(db_session) -> None:
    """
    Verifies that DashboardService aggregates counts, trends, and history correctly.
    """
    # 1. Create a mock Call
    call = Call(
        original_filename="dashboard_test.wav",
        stored_filename="dashboard_test.wav",
        audio_path="./storage/audio/dashboard_test.wav",
        mime_type="audio/wav",
        file_size_bytes=1000,
        duration_seconds=120.0,
        status=CallStatus.Completed,
        language="en"
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    # 2. Create Call Analysis
    analysis = CallAnalysis(
        call_id=call.id,
        overall_score=85,
        summary="Good pacing.",
        recommendation="Maintain script compliance."
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    # 3. Create Issue Tag
    issue = IssueTag(
        analysis_id=analysis.id,
        tag="Weak Discovery",
        severity=Severity.Medium,
        timestamp=2.5,
        quote="Hi there",
        reason="Did not qualify budget"
    )
    db_session.add(issue)
    db_session.commit()

    # Query Dashboard Metrics
    metrics = DashboardService.get_dashboard_metrics(db_session)
    assert metrics["total_calls"] >= 1
    assert metrics["completed_calls"] >= 1
    assert metrics["average_score"] > 0.0

    # Query Trends
    trends = DashboardService.get_score_trends(db_session)
    assert len(trends) >= 1
    assert trends[-1]["score"] == 85

    # Query Issues
    issues = DashboardService.get_issue_distribution(db_session)
    assert len(issues["top_issues"]) >= 1
    assert issues["severity_breakdown"]["Medium"] >= 1

    # Query History
    history = DashboardService.get_history(db_session)
    assert len(history) >= 1
    assert history[0]["filename"] == "dashboard_test.wav"

    # Cleanup
    db_session.delete(issue)
    db_session.delete(analysis)
    db_session.delete(call)
    db_session.commit()

def test_dashboard_service_call_details(db_session) -> None:
    """
    Verifies that call details payloads load correctly.
    """
    call = Call(
        original_filename="details_test.wav",
        stored_filename="details_test.wav",
        audio_path="./storage/audio/details_test.wav",
        mime_type="audio/wav",
        file_size_bytes=200,
        duration_seconds=20.0,
        status=CallStatus.Completed,
        language="en"
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    # Fetch call details
    data = DashboardService.get_call_details(db_session, call.id)
    assert data is not None
    assert data["metadata"]["id"] == call.id
    assert data["metadata"]["duration_seconds"] == 20.0
    assert data["metadata"]["status"] == "Completed"

    # Cleanup
    db_session.delete(call)
    db_session.commit()
