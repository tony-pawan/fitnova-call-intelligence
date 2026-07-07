import os
import pytest  # pyrefly: ignore [missing-import]
import wave
import struct
import math
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient  # pyrefly: ignore [missing-import]
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.call import Call, CallStatus
from backend.app.models.transcript import TranscriptSegment
from backend.app.ai.pyannote_diarizer import PyannoteDiarizer
from backend.app.utils.json_storage import load_json, save_json
from backend.app.services.transcript_storage_service import TranscriptStorageService
from backend.app.ai.dto.transcript import TranscriptResult, TranscriptSegment as DTOTranscriptSegment

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
        tracks = []
        
        # Query database to find the call and determine keyword mapping from original_filename
        db = SessionLocal()
        try:
            filename_base = os.path.basename(audio_path)
            call = db.query(Call).filter(
                (Call.stored_filename == filename_base) | 
                (Call.audio_path == audio_path)
            ).first()
            
            if call:
                orig_lower = call.original_filename.lower()
                if "single" in orig_lower:
                    tracks = [(0.0, 4.0, "SPEAKER_00")]
                elif "two" in orig_lower:
                    tracks = [(0.0, 2.0, "SPEAKER_00"), (2.0, 4.0, "SPEAKER_01")]
                elif "multi" in orig_lower:
                    tracks = [(0.0, 1.5, "SPEAKER_00"), (1.5, 3.0, "SPEAKER_01"), (3.0, 4.5, "SPEAKER_02")]
                elif "silent" in orig_lower:
                    tracks = []
                else:
                    tracks = [(0.0, 2.0, "SPEAKER_00"), (2.0, 4.0, "SPEAKER_01")]
            else:
                tracks = [(0.0, 2.0, "SPEAKER_00"), (2.0, 4.0, "SPEAKER_01")]
        except Exception:
            tracks = [(0.0, 2.0, "SPEAKER_00"), (2.0, 4.0, "SPEAKER_01")]
        finally:
            db.close()
            
        return MockAnnotation(tracks)

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

def test_diarize_missing_token() -> None:
    """
    Verifies that missing Hugging Face authentication token triggers clean validation failure.
    """
    with patch("backend.app.core.config.settings.PYANNOTE_AUTH_TOKEN", ""):
        with pytest.raises(ValueError) as exc:
            PyannoteDiarizer.get_pipeline()
        assert "API token (PYANNOTE_AUTH_TOKEN) is not configured" in str(exc.value)

def test_diarize_missing_transcript() -> None:
    """
    Tests that a missing transcript JSON file fails diarization gracefully.
    """
    diarizer = PyannoteDiarizer()
    with patch("backend.app.ai.pyannote_diarizer.PyannoteDiarizer.get_pipeline") as mock_get:
        mock_get.return_value = MockPyannotePipeline()
        with pytest.raises(FileNotFoundError):
            diarizer.diarize("non_existent_transcript_json.json", "dummy.wav")

def test_diarize_corrupted_transcript() -> None:
    """
    Checks that corrupted transcript file formats throw exceptions correctly.
    """
    temp_path = "./storage/corrupted_test.json"
    os.makedirs("./storage", exist_ok=True)
    with open(temp_path, "w") as f:
        f.write("{invalid_json:")
        
    diarizer = PyannoteDiarizer()
    with patch("backend.app.ai.pyannote_diarizer.PyannoteDiarizer.get_pipeline") as mock_get:
        mock_get.return_value = MockPyannotePipeline()
        with pytest.raises(ValueError):
            diarizer.diarize(temp_path, "dummy.wav")
        
    if os.path.exists(temp_path):
        os.remove(temp_path)

def test_diarize_two_speakers() -> None:
    """
    Verifies end-to-end diarization and conversation mapping logic for two-speaker files.
    """
    os.makedirs("./storage/test_diarize", exist_ok=True)
    audio_path = "./storage/test_diarize/two_speakers.wav"
    generate_wav(audio_path, duration=4.0)
    
    # Mock get_pipeline to return our Mock Pyannote pipeline
    with patch("backend.app.ai.pyannote_diarizer.PyannoteDiarizer.get_pipeline", return_value=MockPyannotePipeline()):
        # Mock Whisper _transcribe to save explicit mock segments
        def mock_transcribe_func(self, db, call):
            result = TranscriptResult(
                language="en",
                duration=4.0,
                segments=[
                    DTOTranscriptSegment(start=0.0, end=2.0, text="Advisor segment text"),
                    DTOTranscriptSegment(start=2.0, end=4.0, text="Customer segment text")
                ]
            )
            call.language = result.language
            db.commit()
            TranscriptStorageService.persist_transcript(db, call.id, result)
            
        with patch("backend.app.pipeline.call_processor.CallProcessor._transcribe", mock_transcribe_func):
            with open(audio_path, "rb") as f:
                response = client.post(
                    "/calls/upload",
                    files={"audio_file": ("two_speakers.wav", f, "audio/wav")}
                )
                
                assert response.status_code == 200
                call_id = response.json()["call_id"]
                
                # Check status
                db = SessionLocal()
                try:
                    call = db.query(Call).filter(Call.id == call_id).first()
                    assert call.status == CallStatus.Completed
                    
                    # Check segments mapped
                    segments = db.query(TranscriptSegment).filter(TranscriptSegment.call_id == call_id).all()
                    assert len(segments) == 2
                    assert segments[0].speaker == "Advisor"
                    assert segments[1].speaker == "Customer"
                    
                    # Check JSON conversation
                    conv_json_path = f"./storage/conversations/call_{call_id}.json"
                    assert os.path.exists(conv_json_path)
                    
                    conv_data = load_json(conv_json_path)
                    assert conv_data["version"] == "1.0"
                    assert conv_data["segments"][0]["speaker"] == "Advisor"
                    assert conv_data["segments"][1]["speaker"] == "Customer"
                finally:
                    db.close()
                    
    if os.path.exists(audio_path):
        os.remove(audio_path)

def test_diarize_single_speaker() -> None:
    """
    Verifies mapping logic fallback when only one speaker is detected.
    """
    os.makedirs("./storage/test_diarize", exist_ok=True)
    audio_path = "./storage/test_diarize/single_speaker.wav"
    generate_wav(audio_path, duration=4.0)
    
    with patch("backend.app.ai.pyannote_diarizer.PyannoteDiarizer.get_pipeline", return_value=MockPyannotePipeline()):
        def mock_transcribe_func(self, db, call):
            result = TranscriptResult(
                language="en",
                duration=4.0,
                segments=[
                    DTOTranscriptSegment(start=0.0, end=4.0, text="Single speaker segment text")
                ]
            )
            call.language = result.language
            db.commit()
            TranscriptStorageService.persist_transcript(db, call.id, result)
            
        with patch("backend.app.pipeline.call_processor.CallProcessor._transcribe", mock_transcribe_func):
            with open(audio_path, "rb") as f:
                response = client.post(
                    "/calls/upload",
                    files={"audio_file": ("single_speaker.wav", f, "audio/wav")}
                )
                
                assert response.status_code == 200
                call_id = response.json()["call_id"]
                
                db = SessionLocal()
                try:
                    call = db.query(Call).filter(Call.id == call_id).first()
                    assert call.status == CallStatus.Completed
                    
                    segments = db.query(TranscriptSegment).filter(TranscriptSegment.call_id == call_id).all()
                    assert len(segments) == 1
                    assert segments[0].speaker == "Speaker 1"
                finally:
                    db.close()
                    
    if os.path.exists(audio_path):
        os.remove(audio_path)

def test_diarize_multi_speakers() -> None:
    """
    Checks that multi-speaker files (3+) are mapped correctly (Advisor, Customer, Speaker 3).
    """
    os.makedirs("./storage/test_diarize", exist_ok=True)
    audio_path = "./storage/test_diarize/multi_speaker.wav"
    generate_wav(audio_path, duration=4.5)
    
    with patch("backend.app.ai.pyannote_diarizer.PyannoteDiarizer.get_pipeline", return_value=MockPyannotePipeline()):
        def mock_transcribe_func(self, db, call):
            result = TranscriptResult(
                language="en",
                duration=4.5,
                segments=[
                    DTOTranscriptSegment(start=0.0, end=1.5, text="Advisor segment text"),
                    DTOTranscriptSegment(start=1.5, end=3.0, text="Customer segment text"),
                    DTOTranscriptSegment(start=3.0, end=4.5, text="Speaker 3 segment text")
                ]
            )
            call.language = result.language
            db.commit()
            TranscriptStorageService.persist_transcript(db, call.id, result)
            
        with patch("backend.app.pipeline.call_processor.CallProcessor._transcribe", mock_transcribe_func):
            with open(audio_path, "rb") as f:
                response = client.post(
                    "/calls/upload",
                    files={"audio_file": ("multi_speaker.wav", f, "audio/wav")}
                )
                
                assert response.status_code == 200
                call_id = response.json()["call_id"]
                
                db = SessionLocal()
                try:
                    call = db.query(Call).filter(Call.id == call_id).first()
                    assert call.status == CallStatus.Completed
                    
                    segments = db.query(TranscriptSegment).filter(TranscriptSegment.call_id == call_id).all()
                    assert len(segments) == 3
                    assert segments[0].speaker == "Advisor"
                    assert segments[1].speaker == "Customer"
                    assert segments[2].speaker == "Speaker 3"
                finally:
                    db.close()
                    
    if os.path.exists(audio_path):
        os.remove(audio_path)

def test_diarize_silent_audio() -> None:
    """
    Checks mapping defaults when no speakers are detected.
    """
    os.makedirs("./storage/test_diarize", exist_ok=True)
    audio_path = "./storage/test_diarize/silent_diarize.wav"
    generate_wav(audio_path, duration=2.0)
    
    with patch("backend.app.ai.pyannote_diarizer.PyannoteDiarizer.get_pipeline", return_value=MockPyannotePipeline()):
        def mock_transcribe_func(self, db, call):
            result = TranscriptResult(
                language="en",
                duration=2.0,
                segments=[
                    DTOTranscriptSegment(start=0.0, end=2.0, text="Mock text segment")
                ]
            )
            call.language = result.language
            db.commit()
            TranscriptStorageService.persist_transcript(db, call.id, result)
            
        with patch("backend.app.pipeline.call_processor.CallProcessor._transcribe", mock_transcribe_func):
            with open(audio_path, "rb") as f:
                response = client.post(
                    "/calls/upload",
                    files={"audio_file": ("silent_diarize.wav", f, "audio/wav")}
                )
                
                assert response.status_code == 200
                call_id = response.json()["call_id"]
                
                db = SessionLocal()
                try:
                    call = db.query(Call).filter(Call.id == call_id).first()
                    assert call.status == CallStatus.Completed
                    
                    segments = db.query(TranscriptSegment).filter(TranscriptSegment.call_id == call_id).all()
                    for s in segments:
                        assert s.speaker == "Speaker 1"
                finally:
                    db.close()
                    
    if os.path.exists(audio_path):
        os.remove(audio_path)
    
    if os.path.exists("./storage/test_diarize"):
        try:
            os.rmdir("./storage/test_diarize")
        except Exception:
            pass
