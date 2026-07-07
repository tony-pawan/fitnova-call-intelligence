import os
import pytest  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.database.session import SessionLocal
from backend.app.models.advisor import Advisor
from backend.app.models.call import Call, CallStatus
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag, Severity
from backend.app.services.dashboard_service import DashboardService
from backend.app.utils.json_storage import save_json

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def existing_advisor(db_session):
    return db_session.query(Advisor).first()

def test_dashboard_service_empty_db(db_session) -> None:
    """
    Verifies that DashboardService returns safe default collections and counts
    when queried on filters that yield empty database results.
    """
    empty_filters = {"advisor_id": -9999}  # Non-existent advisor
    data = DashboardService.get_manager_dashboard(db_session, empty_filters)
    assert data["total_calls"] == 0
    assert data["completed_calls"] == 0
    assert data["average_score"] == 0.0
    assert len(data["recent_calls"]) == 0
    assert len(data["top_issues"]) == 0

def test_dashboard_service_manager_aggregation(db_session, existing_advisor) -> None:
    """
    Verifies that DashboardService aggregates counts, average scores,
    and leaderboard placements correctly.
    """
    assert existing_advisor is not None
    
    # 1. Create a mock Call
    call = Call(
        advisor_id=existing_advisor.id,
        original_filename="dashboard_mgr_test.wav",
        stored_filename="dashboard_mgr_test.wav",
        audio_path="./storage/audio/dashboard_mgr_test.wav",
        mime_type="audio/wav",
        file_size_bytes=1000,
        duration_seconds=10.0,
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
        summary="Good need discovery",
        recommendation="None"
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    # 3. Create Issue Tag
    issue = IssueTag(
        analysis_id=analysis.id,
        tag="Weak Closing",
        severity=Severity.Medium,
        timestamp=2.5,
        quote="Bye",
        reason="Closing was too fast"
    )
    db_session.add(issue)
    db_session.commit()

    # Query Dashboard
    data = DashboardService.get_manager_dashboard(db_session)
    assert data["total_calls"] >= 1
    assert data["completed_calls"] >= 1
    assert data["average_score"] > 0.0
    assert len(data["leaderboard"]) >= 1
    
    # Check leaderboard structure
    adv_lead = next((x for x in data["leaderboard"] if x["advisor_id"] == existing_advisor.id), None)
    assert adv_lead is not None
    assert adv_lead["calls_processed"] >= 1
    
    # Cleanup
    db_session.delete(issue)
    db_session.delete(analysis)
    db_session.delete(call)
    db_session.commit()

def test_dashboard_service_advisor_aggregation(db_session, existing_advisor) -> None:
    """
    Verifies that DashboardService advisor specific dashboard retrieves correct
    scores trend and recommendations lists.
    """
    assert existing_advisor is not None
    
    call = Call(
        advisor_id=existing_advisor.id,
        original_filename="dashboard_adv_test.wav",
        stored_filename="dashboard_adv_test.wav",
        audio_path="./storage/audio/dashboard_adv_test.wav",
        mime_type="audio/wav",
        file_size_bytes=500,
        duration_seconds=5.0,
        status=CallStatus.Completed,
        language="en"
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    analysis = CallAnalysis(
        call_id=call.id,
        overall_score=92,
        summary="Excellent pacing",
        recommendation="Maintain pacing.\nAsk more open questions."
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    # Query Advisor dashboard
    data = DashboardService.get_advisor_dashboard(db_session, existing_advisor.id)
    assert data["average_score"] > 0.0
    assert len(data["recent_calls"]) >= 1
    assert "Maintain pacing." in data["recent_recommendations"]
    assert "Ask more open questions." in data["recent_recommendations"]
    assert len(data["performance_trend"]) >= 1
    
    trend_scores = [t["score"] for t in data["performance_trend"] if t["call_id"] == call.id]
    assert 92 in trend_scores

    # Cleanup
    db_session.delete(analysis)
    db_session.delete(call)
    db_session.commit()

def test_dashboard_service_call_details(db_session, existing_advisor) -> None:
    """
    Verifies that call details payloads load correctly.
    """
    assert existing_advisor is not None
    
    call = Call(
        advisor_id=existing_advisor.id,
        original_filename="details_test.wav",
        stored_filename="details_test.wav",
        audio_path="./storage/audio/details_test.wav",
        mime_type="audio/wav",
        file_size_bytes=200,
        duration_seconds=2.0,
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
    assert data["metadata"]["advisor_name"] == existing_advisor.name
    assert data["metadata"]["duration_seconds"] == 2.0
    assert data["metadata"]["status"] == "Completed"

    # Cleanup
    db_session.delete(call)
    db_session.commit()

def test_dashboard_service_missing_json_artifacts(db_session, existing_advisor) -> None:
    """
    Checks that DashboardService handles missing JSON artifacts (transcripts,
    conversations, timelines) gracefully and returns None for missing blocks.
    """
    assert existing_advisor is not None
    
    call = Call(
        advisor_id=existing_advisor.id,
        original_filename="missing_json_test.wav",
        stored_filename="missing_json_test.wav",
        audio_path="./storage/audio/missing_json_test.wav",
        mime_type="audio/wav",
        file_size_bytes=100,
        duration_seconds=1.0,
        status=CallStatus.Completed,
        language="en"
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    # Fetch details for this call which has no JSON files written under storage/
    data = DashboardService.get_call_details(db_session, call.id)
    assert data is not None
    assert data["transcript"] is None
    assert data["conversation"] is None
    assert data["analysis"] is None
    assert isinstance(data["timeline"], list)  # Timeline returns empty list instead of None

    # Cleanup
    db_session.delete(call)
    db_session.commit()

def test_dashboard_service_filters(db_session, existing_advisor) -> None:
    """
    Verifies that DashboardService respects search filters (advisor_id,
    status, min_score, and search_id).
    """
    assert existing_advisor is not None
    
    call = Call(
        advisor_id=existing_advisor.id,
        original_filename="filter_test.wav",
        stored_filename="filter_test.wav",
        audio_path="./storage/audio/filter_test.wav",
        mime_type="audio/wav",
        file_size_bytes=400,
        duration_seconds=4.0,
        status=CallStatus.Completed,
        language="en"
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    analysis = CallAnalysis(
        call_id=call.id,
        overall_score=75,
        summary="Average score",
        recommendation="Try harder."
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    # 1. Filter by status == Processing (should be empty for our call)
    data_proc = DashboardService.get_manager_dashboard(db_session, {"status": "Processing"})
    found_proc = [c for c in data_proc["recent_calls"] if c["id"] == call.id]
    assert len(found_proc) == 0

    # 2. Filter by status == Completed (should find our call)
    data_comp = DashboardService.get_manager_dashboard(db_session, {"status": "Completed"})
    found_comp = [c for c in data_comp["recent_calls"] if c["id"] == call.id]
    assert len(found_comp) >= 1

    # 3. Filter by min_score == 80 (should be empty for our score of 75)
    data_score_high = DashboardService.get_manager_dashboard(db_session, {"min_score": 80})
    found_high = [c for c in data_score_high["recent_calls"] if c["id"] == call.id]
    assert len(found_high) == 0

    # 4. Filter by min_score == 70 (should include our score of 75)
    data_score_low = DashboardService.get_manager_dashboard(db_session, {"min_score": 70})
    found_low = [c for c in data_score_low["recent_calls"] if c["id"] == call.id]
    assert len(found_low) >= 1

    # 5. Filter by search_id == call.id (should match exactly)
    data_search = DashboardService.get_manager_dashboard(db_session, {"search_id": str(call.id)})
    assert len(data_search["recent_calls"]) == 1
    assert data_search["recent_calls"][0]["id"] == call.id

    # Cleanup
    db_session.delete(analysis)
    db_session.delete(call)
    db_session.commit()
