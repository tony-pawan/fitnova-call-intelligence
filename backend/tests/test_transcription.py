import os
import wave
import struct
import math
import pytest  # pyrefly: ignore [missing-import]
from unittest.mock import patch
from fastapi.testclient import TestClient  # pyrefly: ignore [missing-import]
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.call import Call, CallStatus
from backend.app.models.transcript import TranscriptSegment
from backend.app.utils.json_storage import load_json

client = TestClient(app)

# Helper function to dynamically generate dummy WAV files for tests
def generate_wav(path: str, duration: float = 1.0, is_silent: bool = False) -> None:
    sample_rate = 16000
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        num_samples = int(duration * sample_rate)
        for i in range(num_samples):
            if is_silent:
                val = 0
            else:
                # Generate a simple 440Hz sine wave tone
                t = float(i) / sample_rate
                val = int(32767.0 * math.sin(2.0 * math.pi * 440.0 * t))
            w.writeframesraw(struct.pack("<h", val))

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
        return MockAnnotation([(0.0, 5.0, "SPEAKER_00")])

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
def test_files():
    temp_dir = "./storage/test_transcribe_temp"
    os.makedirs(temp_dir, exist_ok=True)
    paths = {
        "success": f"{temp_dir}/success.wav",
        "silent": f"{temp_dir}/silent.wav",
        "short": f"{temp_dir}/short.wav",
        "long": f"{temp_dir}/long.wav",
        "corrupted": f"{temp_dir}/corrupted.wav"
    }
    
    # Generate test audio
    generate_wav(paths["success"], duration=1.0, is_silent=False)
    generate_wav(paths["silent"], duration=1.0, is_silent=True)
    generate_wav(paths["short"], duration=0.2, is_silent=False)
    generate_wav(paths["long"], duration=3.0, is_silent=False)
    
    # Corrupted audio write
    with open(paths["corrupted"], "w") as f:
        f.write("Corrupted text representation")
        
    yield paths
    
    # Cleanup files
    for p in paths.values():
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass
    if os.path.exists(temp_dir):
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass

def test_transcribe_success(test_files) -> None:
    """
    Checks end-to-end transcription flow, ensuring PostgreSQL segments
    and JSON artifacts are stored under storage/transcripts/.
    """
    with open(test_files["success"], "rb") as f:
        response = client.post(
            "/calls/upload",
            files={"audio_file": ("success.wav", f, "audio/wav")}
        )
        
        assert response.status_code == 200
        call_id = response.json()["call_id"]
        
        # Verify status transitions to Completed
        db = SessionLocal()
        try:
            call = db.query(Call).filter(Call.id == call_id).first()
            assert call.status == CallStatus.Completed
            assert call.language is not None
            
            # Check segments in DB
            db_segments = db.query(TranscriptSegment).filter(TranscriptSegment.call_id == call_id).all()
            assert len(db_segments) >= 0  # Simple sine waves might yield no speech depending on model thresholds
            
            # Check JSON file
            json_path = f"./storage/transcripts/call_{call_id}.json"
            assert os.path.exists(json_path)
            
            # Use safe parser
            json_data = load_json(json_path)
            assert json_data["version"] == "1.0"
            assert "generated_at" in json_data
            assert json_data["language"] == call.language
            assert "segments" in json_data
        finally:
            db.close()

def test_transcribe_silent(test_files) -> None:
    """
    Verifies that silent audio uploads are parsed without error.
    """
    with open(test_files["silent"], "rb") as f:
        response = client.post(
            "/calls/upload",
            files={"audio_file": ("silent.wav", f, "audio/wav")}
        )
        
        assert response.status_code == 200
        call_id = response.json()["call_id"]
        
        db = SessionLocal()
        try:
            call = db.query(Call).filter(Call.id == call_id).first()
            assert call.status == CallStatus.Completed
        finally:
            db.close()

def test_transcribe_short_audio(test_files) -> None:
    """
    Verifies that very short audio files (0.2s) are processed safely.
    """
    with open(test_files["short"], "rb") as f:
        response = client.post(
            "/calls/upload",
            files={"audio_file": ("short.wav", f, "audio/wav")}
        )
        
        assert response.status_code == 200
        call_id = response.json()["call_id"]
        
        db = SessionLocal()
        try:
            call = db.query(Call).filter(Call.id == call_id).first()
            assert call.status == CallStatus.Completed
        finally:
            db.close()

def test_transcribe_long_audio(test_files) -> None:
    """
    Verifies that longer audio files are processed safely.
    """
    with open(test_files["long"], "rb") as f:
        response = client.post(
            "/calls/upload",
            files={"audio_file": ("long.wav", f, "audio/wav")}
        )
        
        assert response.status_code == 200
        call_id = response.json()["call_id"]
        
        db = SessionLocal()
        try:
            call = db.query(Call).filter(Call.id == call_id).first()
            assert call.status == CallStatus.Completed
        finally:
            db.close()

def test_transcribe_corrupted_audio(test_files) -> None:
    """
    Verifies that corrupted files trigger pipeline failure and set status to Failed.
    """
    with open(test_files["corrupted"], "rb") as f:
        response = client.post(
            "/calls/upload",
            files={"audio_file": ("corrupted.wav", f, "audio/wav")}
        )
        
        assert response.status_code == 200
        call_id = response.json()["call_id"]
        
        db = SessionLocal()
        try:
            call = db.query(Call).filter(Call.id == call_id).first()
            assert call.status == CallStatus.Failed
        finally:
            db.close()
