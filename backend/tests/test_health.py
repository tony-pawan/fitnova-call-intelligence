from fastapi.testclient import TestClient  # pyrefly: ignore [missing-import]
from backend.app.main import app

client = TestClient(app)

def test_health_check() -> None:
    """
    Verifies that the /health endpoint is online and returns the expected status.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
