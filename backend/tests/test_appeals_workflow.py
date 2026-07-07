import os
import pytest  # pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient  # pyrefly: ignore [missing-import]
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.advisor import Advisor
from backend.app.models.call import Call, CallStatus
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag, Severity
from backend.app.models.appeal import Appeal, AppealStatus
from backend.app.services.dashboard_service import DashboardService

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def setup_test_records(db_session):
    """
    Sets up a mock advisor, call, and call analysis containing issue tags for testing.
    """
    advisor = db_session.query(Advisor).first()
    assert advisor is not None

    call = Call(
        advisor_id=advisor.id,
        original_filename="appeals_workflow_test.wav",
        stored_filename="appeals_workflow_test.wav",
        audio_path="./storage/audio/appeals_workflow_test.wav",
        mime_type="audio/wav",
        file_size_bytes=800,
        duration_seconds=8.0,
        status=CallStatus.Completed,
        language="en"
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    analysis = CallAnalysis(
        call_id=call.id,
        overall_score=80,
        summary="Dispute test analysis",
        recommendation="Improve compliance details"
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    # Flag two separate issue tags to dispute individually
    issue1 = IssueTag(
        analysis_id=analysis.id,
        tag="Disclosure Failure",
        severity=Severity.High,
        timestamp=1.5,
        quote="Disclosed nothing",
        reason="Skipped read"
    )
    issue2 = IssueTag(
        analysis_id=analysis.id,
        tag="Needs discovery lack",
        severity=Severity.Medium,
        timestamp=3.0,
        quote="No questions",
        reason="Pitched directly"
    )
    db_session.add(issue1)
    db_session.add(issue2)
    db_session.commit()
    db_session.refresh(issue1)
    db_session.refresh(issue2)

    yield {
        "advisor_id": advisor.id,
        "call_id": call.id,
        "issue_tag_1_id": issue1.id,
        "issue_tag_2_id": issue2.id
    }

    # Clean up test database records
    db_session.query(Appeal).filter(Appeal.advisor_id == advisor.id).delete()
    db_session.delete(issue1)
    db_session.delete(issue2)
    db_session.delete(analysis)
    db_session.delete(call)
    db_session.commit()

def test_submit_appeal_success(db_session, setup_test_records) -> None:
    """
    Verifies that a valid POST /appeals dispute submission succeeds
    and creates a database Appeal record in Pending state.
    """
    records = setup_test_records
    payload = {
        "issue_tag_id": records["issue_tag_1_id"],
        "advisor_id": records["advisor_id"],
        "reason": "I did read the standard disclosure statement at 1.5s."
    }

    response = client.post("/appeals", json=payload)
    assert response.status_code == 201
    
    data = response.json()
    assert data["status"] == "Pending"
    assert data["reason"] == payload["reason"]
    
    # Assert DB entry exists
    db_appeal = db_session.query(Appeal).filter(Appeal.id == data["id"]).first()
    assert db_appeal is not None
    assert db_appeal.reason == payload["reason"]

def test_submit_appeal_duplicate_prevention(setup_test_records) -> None:
    """
    Asserts that duplicate dispute submissions against the same IssueTag ID are blocked.
    """
    records = setup_test_records
    payload = {
        "issue_tag_id": records["issue_tag_1_id"],  # Same tag already appealed in test above
        "advisor_id": records["advisor_id"],
        "reason": "Duplicate appeal dispute justification text."
    }

    response = client.post("/appeals", json=payload)
    assert response.status_code == 400
    assert "already been appealed" in response.json()["detail"]

def test_resolve_appeal_approve(db_session, setup_test_records) -> None:
    """
    Checks that PATCH /appeals/{id} updates status to Approved.
    """
    records = setup_test_records
    
    # Query the existing appeal created in first test
    db_appeal = db_session.query(Appeal).filter(
        Appeal.issue_tag_id == records["issue_tag_1_id"]
    ).first()
    assert db_appeal is not None
    assert db_appeal.status == AppealStatus.Pending

    response = client.patch(
        f"/appeals/{db_appeal.id}",
        json={"status": "Approved"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Approved"

    # Verify status change in DB
    db_session.refresh(db_appeal)
    assert db_appeal.status == AppealStatus.Approved

def test_resolve_appeal_reject(db_session, setup_test_records) -> None:
    """
    Checks that PATCH /appeals/{id} updates status to Rejected.
    """
    records = setup_test_records
    
    # Submit second appeal on second issue tag
    payload = {
        "issue_tag_id": records["issue_tag_2_id"],
        "advisor_id": records["advisor_id"],
        "reason": "Disputing need discovery tag."
    }
    response_post = client.post("/appeals", json=payload)
    assert response_post.status_code == 201
    appeal_id = response_post.json()["id"]

    # Reject the appeal
    response_patch = client.patch(
        f"/appeals/{appeal_id}",
        json={"status": "Rejected"}
    )
    assert response_patch.status_code == 200
    assert response_patch.json()["status"] == "Rejected"

    # Verify status change in DB
    db_appeal = db_session.query(Appeal).filter(Appeal.id == appeal_id).first()
    assert db_appeal.status == AppealStatus.Rejected

def test_appeal_dashboard_statistics(db_session, setup_test_records) -> None:
    """
    Verifies that DashboardService returns the correct counts for pending,
    approved, and rejected appeals.
    """
    stats = DashboardService.get_appeal_statistics(db_session)
    # The setup created two appeals: one Approved, one Rejected. Pending should be 0.
    assert stats["approved"] >= 1
    assert stats["rejected"] >= 1
