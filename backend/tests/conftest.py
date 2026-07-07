import pytest
from backend.app.core.config import settings

@pytest.fixture(autouse=True)
def mock_gemini_settings():
    """
    Globally mocks settings for all pytest runs to bypass live external Gemini API.
    """
    original_key = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = "mock_key_for_development"
    yield
    settings.GEMINI_API_KEY = original_key
