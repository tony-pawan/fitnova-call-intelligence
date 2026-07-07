import pytest  # pyrefly: ignore [missing-import]
from unittest.mock import patch
from fastapi.testclient import TestClient  # pyrefly: ignore [missing-import]
from backend.app.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.advisor import Advisor

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def existing_advisor(db_session):
    advisor = db_session.query(Advisor).first()
    return advisor

def test_upload_success(existing_advisor) -> None:
    """
    Verifies that a valid audio file (e.g. WAV format) is uploaded successfully,
    registers in the database, and returns the expected payload.
    """
    assert existing_advisor is not None, "Seeded advisor is required for upload testing."
    
    file_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x22\x56\x00\x00\x44\xAC\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    
    with patch("backend.app.services.upload_service.extract_audio_metadata") as mock_extract:
        mock_extract.return_value = {"duration_seconds": 15.5}
        
        response = client.post(
            "/calls/upload",
            data={"advisor_id": existing_advisor.id},
            files={"audio_file": ("test_recording.wav", file_content, "audio/wav")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "call_id" in data
        assert data["status"] == "Uploaded"
        assert data["original_filename"] == "test_recording.wav"
        assert data["duration_seconds"] == 15.5

def test_upload_unsupported_file_extension(existing_advisor) -> None:
    """
    Checks that uploading files with invalid extensions (e.g. .png) fails with 400 Bad Request.
    """
    response = client.post(
        "/calls/upload",
        data={"advisor_id": existing_advisor.id},
        files={"audio_file": ("charts.png", b"fake_png_data", "image/png")}
    )
    
    assert response.status_code == 400
    assert "Unsupported file type extension" in response.json()["detail"]

def test_upload_oversized_upload(existing_advisor) -> None:
    """
    Ensures uploading files larger than 100 MB is rejected with 400 Bad Request.
    """
    # 101 MB of mock bytes
    oversized_data = b"x" * (101 * 1024 * 1024)
    response = client.post(
        "/calls/upload",
        data={"advisor_id": existing_advisor.id},
        files={"audio_file": ("long_call.wav", oversized_data, "audio/wav")}
    )
    
    assert response.status_code == 400
    assert "exceeds maximum limit of 100 MB" in response.json()["detail"]

def test_upload_invalid_advisor() -> None:
    """
    Verifies that uploading for a non-existent advisor ID raises 404 Not Found.
    """
    response = client.post(
        "/calls/upload",
        data={"advisor_id": 999999},
        files={"audio_file": ("call.mp3", b"fake_mp3_data", "audio/mpeg")}
    )
    
    assert response.status_code == 404
    assert "Advisor with ID 999999 not found" in response.json()["detail"]

def test_get_calls() -> None:
    """
    Verifies the list call log route GET /calls returns successfully.
    """
    response = client.get("/calls")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_call_by_id(existing_advisor) -> None:
    """
    Tests details querying for a specific call ID.
    """
    file_content = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    
    with patch("backend.app.services.upload_service.extract_audio_metadata") as mock_extract:
        mock_extract.return_value = {"duration_seconds": 45.2}
        
        # Upload first
        up_response = client.post(
            "/calls/upload",
            data={"advisor_id": existing_advisor.id},
            files={"audio_file": ("test_details.wav", file_content, "audio/wav")}
        )
        call_id = up_response.json()["call_id"]
        
        # Fetch detail
        detail_response = client.get(f"/calls/{call_id}")
        assert detail_response.status_code == 200
        data = detail_response.json()
        assert data["id"] == call_id
        assert data["original_filename"] == "test_details.wav"
        assert data["advisor_id"] == existing_advisor.id
        assert data["duration_seconds"] == 45.2
