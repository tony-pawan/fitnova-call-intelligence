import pytest  # pyrefly: ignore [missing-import]
import os
from unittest.mock import patch
from fastapi.testclient import TestClient  # pyrefly: ignore [missing-import]
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.advisor import Advisor
from backend.app.models.call import Call, CallStatus
from backend.app.utils.timeline import get_pipeline_timeline

client = TestClient(app)

# Helper mock classes for Pyannote speaker tracks mapping
class MockTurn:
    def __init__(self, start: float, end: float) -> None:
        self.start = start
        self.end = end

class MockAnnotation:
    def __init__(self, tracks) -> None:
        self.tracks = tracks

    def itertracks(self, yield_label: bool = True):
        for start, end, label in self.tracks:
            yield MockTurn(start, end), None, label

class MockPyannotePipeline:
    def __call__(self, audio_path: str) -> MockAnnotation:
        return MockAnnotation([(0.0, 2.0, "SPEAKER_00"), (2.0, 4.0, "SPEAKER_01")])

@pytest.fixture(autouse=True)
def mock_pyannote_downloader():
    with patch("backend.app.ai.pyannote_diarizer.PyannoteDiarizer.get_pipeline") as mock_get:
        mock_get.return_value = MockPyannotePipeline()
        yield mock_get

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

def test_pipeline_success(existing_advisor) -> None:
    """
    Verifies that a successful upload triggers the background processing task,
    running through intermediate states and ending up as Completed.
    """
    assert existing_advisor is not None
    
    file_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x22\x56\x00\x00\x44\xAC\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    
    # Mock extract_audio_metadata to bypass mutagen check
    with patch("backend.app.services.upload_service.extract_audio_metadata") as mock_extract:
        mock_extract.return_value = {"duration_seconds": 12.0}
        
        # Mock transcription, diarization, and analysis stages to bypass VAD silence filter and filesystem requirements
        with patch("backend.app.pipeline.call_processor.CallProcessor._transcribe") as mock_trans, \
             patch("backend.app.pipeline.call_processor.CallProcessor._diarize") as mock_diarize, \
             patch("backend.app.pipeline.call_processor.CallProcessor._analyze") as mock_analyze:
                 
            response = client.post(
                "/calls/upload",
                data={"advisor_id": existing_advisor.id},
                files={"audio_file": ("pipeline_ok.wav", file_content, "audio/wav")}
            )
            
            assert response.status_code == 200
            data = response.json()
            call_id = data["call_id"]
            
            # Immediately check DB status - it should be Completed because BackgroundTasks
            # ran synchronously during the test client lifecycle.
            db = SessionLocal()
            try:
                db_call = db.query(Call).filter(Call.id == call_id).first()
                assert db_call is not None
                assert db_call.status == CallStatus.Completed
            finally:
                db.close()
                
            # Verify timeline events were generated
            timeline = get_pipeline_timeline(call_id)
            events = [t["event"] for t in timeline]
            assert "Queued" in events
            assert "Processing Started" in events
            assert "Completed" in events

def test_pipeline_failure_handling(existing_advisor) -> None:
    """
    Verifies that if any step inside the pipeline raises an exception,
    the pipeline intercepts it, changes status to Failed, and logs timeline/exceptions.
    """
    assert existing_advisor is not None
    
    file_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x22\x56\x00\x00\x44\xAC\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    
    with patch("backend.app.services.upload_service.extract_audio_metadata") as mock_extract:
        mock_extract.return_value = {"duration_seconds": 5.0}
        
        # Mock _transcribe to raise an intentional exception
        with patch("backend.app.pipeline.call_processor.CallProcessor._transcribe", side_effect=ValueError("Mock transcription failure")):
            response = client.post(
                "/calls/upload",
                data={"advisor_id": existing_advisor.id},
                files={"audio_file": ("pipeline_err.wav", file_content, "audio/wav")}
            )
            
            assert response.status_code == 200
            data = response.json()
            call_id = data["call_id"]
            
            # Re-check status in DB - must be Failed
            db = SessionLocal()
            try:
                db_call = db.query(Call).filter(Call.id == call_id).first()
                assert db_call is not None
                assert db_call.status == CallStatus.Failed
            finally:
                db.close()
                
            # Verify timeline ends with Failed
            timeline = get_pipeline_timeline(call_id)
            events = [t["event"] for t in timeline]
            assert "Queued" in events
            assert "Processing Started" in events
            assert "Failed" in events
            assert "Completed" not in events
