import os
import shutil
import pytest  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import sessionmaker  # pyrefly: ignore [missing-import]
from backend.app.database.base import Base
from backend.app.database.database import engine
from backend.app.models.call import Call, CallStatus
from backend.app.models.transcript import TranscriptSegment
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag
from backend.app.models.version_models import TranscriptVersion, ConversationVersion, AnalysisVersion
from backend.app.ingestion.dto import AudioInput
from backend.app.ingestion.connectors.upload_connector import UploadConnector
from backend.app.ingestion.connectors.folder_connector import FolderConnector
from backend.app.ingestion.connectors.crm_connector import CRMConnector
from backend.app.ingestion.connectors.telephony_connector import TelephonyConnector
from backend.app.ingestion.connectors.dialer_connector import DialerConnector
from backend.app.ingestion.orchestrator import IngestionOrchestrator
from backend.app.services.feedback_service import FeedbackService
from backend.app.utils.json_storage import save_json, load_json

# Setup test DB
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    # Make sure tables exist
    from backend.app.database.init_db import init_db
    init_db()
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_upload_connector_normalizes_correctly():
    connector = UploadConnector(
        filename="test_call.mp3",
        temp_path="C:/Users/Admin/Desktop/novafit/good call recording synthetic data.mp3",
        size_bytes=1000,
        metadata={"customer_name": "Test Customer", "advisor_name": "Test Advisor"}
    )
    assert connector.connect() is True
    
    # We won't trigger fetch unless file actually exists, but we can test normalize directly
    dto = connector.normalize({
        "audio_path": "path",
        "original_filename": "test_call.mp3",
        "mime_type": "audio/mp3",
        "metadata": {"customer_name": "Test Customer", "advisor_name": "Test Advisor"}
    })
    assert dto.source == "Upload"
    assert dto.customer_name == "Test Customer"
    assert dto.advisor_name == "Test Advisor"

def test_telephony_connector_simulates_fetch():
    connector = TelephonyConnector(vendor="Twilio", config={"api_key": "simulated"})
    assert connector.connect() is True
    
    dtos = connector.fetch()
    assert len(dtos) == 1
    dto = dtos[0]
    assert dto.source == "Telephony"
    assert dto.vendor == "Twilio"
    assert dto.mime_type == "audio/mp3"
    assert dto.external_call_id is not None
    assert dto.customer_name is not None
    assert dto.advisor_name is not None

def test_dialer_connector_simulates_fetch():
    connector = DialerConnector(vendor="Five9", config={"api_key": "simulated"})
    assert connector.connect() is True
    
    dtos = connector.fetch()
    assert len(dtos) == 1
    dto = dtos[0]
    assert dto.source == "Dialer"
    assert dto.vendor == "Five9"
    assert dto.mime_type == "audio/mp3"
    assert dto.external_call_id is not None

def test_feedback_service_versions_and_overrides(db_session):
    # Register mock call in db
    call = Call(
        original_filename="feedback_test.mp3",
        stored_filename="call_9999.mp3",
        audio_path="./storage/audio/call_9999.mp3",
        mime_type="audio/mp3",
        file_size_bytes=1024,
        duration_seconds=10.0,
        status=CallStatus.Completed,
        source="Upload",
        vendor="Direct"
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)
    
    # Setup mock active file paths
    os.makedirs("./storage/transcripts", exist_ok=True)
    os.makedirs("./storage/conversations", exist_ok=True)
    os.makedirs("./storage/analysis", exist_ok=True)
    
    t_path = f"./storage/transcripts/call_{call.id}.json"
    c_path = f"./storage/conversations/call_{call.id}.json"
    a_path = f"./storage/analysis/call_{call.id}.json"
    
    save_json(t_path, {"segments": [{"start": 0.0, "end": 2.0, "text": "Purani text"}]})
    save_json(c_path, {"segments": [{"speaker": "Advisor", "start": 0.0, "end": 2.0, "text": "Purani text"}]})
    save_json(a_path, {"overall_score": 75.0, "summary": "Key strengths"})
    
    # Add dummy analysis db row
    analysis = CallAnalysis(call_id=call.id, overall_score=75, summary="Dummy summary", recommendation="Dummy rec")
    db_session.add(analysis)
    db_session.commit()
    
    # Test transcript correction
    FeedbackService.correct_transcript(db_session, call.id, [{"index": 0, "text": "Naya path text"}])
    updated_t = load_json(t_path)
    assert updated_t["segments"][0]["text"] == "Naya path text"
    
    # Test speaker correction
    FeedbackService.correct_speakers(db_session, call.id, [{"index": 0, "speaker": "Customer"}])
    updated_c = load_json(c_path)
    assert updated_c["segments"][0]["speaker"] == "Customer"
    
    # Test score override
    FeedbackService.override_score(db_session, call.id, 92.0, "Approved override", "Lead Reviewer")
    db_session.refresh(analysis)
    assert analysis.overall_score == 92
    
    # Cleanup dummy files & db
    for path in [t_path, c_path, a_path]:
        if os.path.exists(path):
            os.remove(path)
            
    # Clean versioned files if generated
    v1_t = f"./storage/transcripts/call_{call.id}_v1.json"
    v2_t = f"./storage/transcripts/call_{call.id}_v2.json"
    v1_c = f"./storage/conversations/call_{call.id}_v1.json"
    v2_c = f"./storage/conversations/call_{call.id}_v2.json"
    v1_a = f"./storage/analysis/call_{call.id}_v1.json"
    v2_a = f"./storage/analysis/call_{call.id}_v2.json"
    for path in [v1_t, v2_t, v1_c, v2_c, v1_a, v2_a]:
        if os.path.exists(path):
            os.remove(path)
            
    db_session.delete(analysis)
    db_session.delete(call)
    db_session.commit()
