import os
import wave
import struct
import math
import pytest  # pyrefly: ignore [missing-import]
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient  # pyrefly: ignore [missing-import]
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.call import Call, CallStatus
from backend.app.models.analysis import CallAnalysis
from backend.app.models.issue_tag import IssueTag
from backend.app.utils.json_storage import load_json, save_json
from backend.app.ai.llm.gemini_client import GeminiClient
from backend.app.ai.dto.conversation import ConversationResult, ConversationSegment
from backend.app.ai.analysis_orchestrator import AnalysisOrchestrator

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

def generate_wav(path: str, duration: float = 1.0) -> None:
    sample_rate = 16000
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        num_samples = int(duration * sample_rate)
        for i in range(num_samples):
            t = float(i) / sample_rate
            val = int(32767.0 * math.sin(2.0 * math.pi * 440.0 * t))
            w.writeframesraw(struct.pack("<h", val))

def test_analysis_success() -> None:
    """
    Verifies that a complete pipeline run automatically triggers Gemini analysis,
    generates database records, and creates versioned JSON scorecards.
    """
    os.makedirs("./storage/test_analysis", exist_ok=True)
    audio_path = "./storage/test_analysis/success_analysis.wav"
    generate_wav(audio_path, duration=4.0)

    # Mock transcription stage
    from backend.app.ai.dto.transcript import TranscriptResult, TranscriptSegment as DTOTranscriptSegment
    from backend.app.services.transcript_storage_service import TranscriptStorageService
    
    def mock_transcribe_func(self, db, call):
        result = TranscriptResult(
            language="en",
            duration=4.0,
            segments=[
                DTOTranscriptSegment(start=0.0, end=2.0, text="Disclosures segment"),
                DTOTranscriptSegment(start=2.0, end=4.0, text="Discovery segment")
            ]
        )
        call.language = result.language
        db.commit()
        TranscriptStorageService.persist_transcript(db, call.id, result)

    with patch("backend.app.pipeline.call_processor.CallProcessor._transcribe", mock_transcribe_func):
        with open(audio_path, "rb") as f:
            response = client.post(
                "/calls/upload",
                files={"audio_file": ("success_analysis.wav", f, "audio/wav")}
            )
            
            assert response.status_code == 200
            call_id = response.json()["call_id"]
            
            # Immediately query DB to check Completed status
            db = SessionLocal()
            try:
                call = db.query(Call).filter(Call.id == call_id).first()
                assert call.status == CallStatus.Completed
                
                # Check DB persistence (CallAnalysis)
                analysis = db.query(CallAnalysis).filter(CallAnalysis.call_id == call_id).first()
                assert analysis is not None
                assert analysis.overall_score == 84  # Average of 82 (discovery), 95 (compliance), 75 (sales) -> 84.0
                assert "Discovery" in analysis.summary
                assert "disclosures" in analysis.recommendation or "objection" in analysis.recommendation
                
                # Check DB persistence (IssueTags)
                db_tags = db.query(IssueTag).filter(IssueTag.analysis_id == analysis.id).all()
                tags = [t.tag for t in db_tags]
                assert "Missing Budget Discovery" in tags
                assert "Weak Objection Handling" in tags
                
                # Check filesystem JSON storage scorecard
                json_path = f"./storage/analysis/call_{call_id}.json"
                assert os.path.exists(json_path)
                
                json_data = load_json(json_path)
                assert json_data["version"] == "1.0"
                assert json_data["overall_score"] == 84.0
                assert len(json_data["strengths"]) > 0
                assert json_data["analysis_metadata"]["completed_analyzers"] == ["discovery", "compliance", "sales_quality"]
            finally:
                db.close()

    if os.path.exists(audio_path):
        os.remove(audio_path)

def test_analysis_json_repair_retry() -> None:
    """
    Checks that malformed JSON triggers the validation retry, repairs successfully, and parses the correct values.
    """
    mock_client = MagicMock()
    # First returns malformed JSON, second returns valid JSON (repair request)
    mock_client.generate.side_effect = [
        "{ malformed_json: true ",
        json.dumps({
            "score": 90.0,
            "summary": "Repaired summary",
            "strengths": ["Strong objection handling"],
            "weaknesses": [],
            "recommendations": ["None"],
            "issue_tags": []
        })
    ]
    
    from backend.app.ai.analyzers import DiscoveryAnalyzer
    analyzer = DiscoveryAnalyzer(mock_client)
    
    conversation = ConversationResult(
        language="en",
        duration=5.0,
        segments=[
            ConversationSegment(speaker="Advisor", start=0.0, end=5.0, text="Hello world")
        ]
    )
    
    res = analyzer.analyze(conversation)
    assert res.score == 90.0
    assert res.summary == "Repaired summary"
    assert "Strong objection handling" in res.strengths
    # Assert get_pipeline called twice (first generate, second repair generate)
    assert mock_client.generate.call_count == 2

def test_analysis_partial_failures() -> None:
    """
    Verifies that a single analyzer failure (e.g. Compliance fails) is tolerated,
    and overall score is computed from the successful analyzers (Discovery + Sales Quality).
    """
    os.makedirs("./storage/test_analysis", exist_ok=True)
    audio_path = "./storage/test_analysis/partial_analysis.wav"
    generate_wav(audio_path, duration=4.0)

    from backend.app.ai.dto.transcript import TranscriptResult, TranscriptSegment as DTOTranscriptSegment
    from backend.app.services.transcript_storage_service import TranscriptStorageService
    
    def mock_transcribe_func(self, db, call):
        result = TranscriptResult(
            language="en",
            duration=4.0,
            segments=[
                DTOTranscriptSegment(start=0.0, end=2.0, text="Advisor segment"),
                DTOTranscriptSegment(start=2.0, end=4.0, text="Customer segment")
            ]
        )
        call.language = result.language
        db.commit()
        TranscriptStorageService.persist_transcript(db, call.id, result)

    # Mock compliance analyzer to throw an exception
    with patch("backend.app.ai.analyzers.compliance_analyzer.ComplianceAnalyzer.analyze", side_effect=ValueError("Compliance failure")):
        with patch("backend.app.pipeline.call_processor.CallProcessor._transcribe", mock_transcribe_func):
            with open(audio_path, "rb") as f:
                response = client.post(
                    "/calls/upload",
                    files={"audio_file": ("partial_analysis.wav", f, "audio/wav")}
                )
                
                assert response.status_code == 200
                call_id = response.json()["call_id"]
                
                # DB check
                db = SessionLocal()
                try:
                    call = db.query(Call).filter(Call.id == call_id).first()
                    assert call.status == CallStatus.Completed
                    
                    # Overall score should be average of Discovery (82.0) and Sales Quality (75.0) -> 78.5
                    analysis = db.query(CallAnalysis).filter(CallAnalysis.call_id == call_id).first()
                    assert analysis.overall_score in [78, 79]
                    
                    # Verify metadata shows compliance failed
                    json_path = f"./storage/analysis/call_{call_id}.json"
                    json_data = load_json(json_path)
                    assert "compliance" in json_data["analysis_metadata"]["failed_analyzers"]
                    assert "discovery" in json_data["analysis_metadata"]["completed_analyzers"]
                finally:
                    db.close()

    if os.path.exists(audio_path):
        os.remove(audio_path)

def test_analysis_complete_failure() -> None:
    """
    Verifies that if ALL analyzers fail, the pipeline fails gracefully and call status becomes Failed.
    """
    os.makedirs("./storage/test_analysis", exist_ok=True)
    audio_path = "./storage/test_analysis/complete_fail_analysis.wav"
    generate_wav(audio_path, duration=4.0)

    from backend.app.ai.dto.transcript import TranscriptResult, TranscriptSegment as DTOTranscriptSegment
    from backend.app.services.transcript_storage_service import TranscriptStorageService
    
    def mock_transcribe_func(self, db, call):
        result = TranscriptResult(
            language="en",
            duration=4.0,
            segments=[
                DTOTranscriptSegment(start=0.0, end=2.0, text="Advisor segment"),
                DTOTranscriptSegment(start=2.0, end=4.0, text="Customer segment")
            ]
        )
        call.language = result.language
        db.commit()
        TranscriptStorageService.persist_transcript(db, call.id, result)

    # Mock all three analyzers to throw errors
    with patch("backend.app.ai.analyzers.discovery_analyzer.DiscoveryAnalyzer.analyze", side_effect=RuntimeError("Discovery down")), \
         patch("backend.app.ai.analyzers.compliance_analyzer.ComplianceAnalyzer.analyze", side_effect=RuntimeError("Compliance down")), \
         patch("backend.app.ai.analyzers.sales_quality_analyzer.SalesQualityAnalyzer.analyze", side_effect=RuntimeError("Sales quality down")):
              
        with patch("backend.app.pipeline.call_processor.CallProcessor._transcribe", mock_transcribe_func):
            with open(audio_path, "rb") as f:
                response = client.post(
                    "/calls/upload",
                    files={"audio_file": ("complete_fail_analysis.wav", f, "audio/wav")}
                )
                
                assert response.status_code == 200
                call_id = response.json()["call_id"]
                
                db = SessionLocal()
                try:
                    call = db.query(Call).filter(Call.id == call_id).first()
                    assert call.status == CallStatus.Failed
                finally:
                    db.close()

    if os.path.exists(audio_path):
        os.remove(audio_path)
        
    if os.path.exists("./storage/test_analysis"):
        try:
            os.rmdir("./storage/test_analysis")
        except Exception:
            pass
