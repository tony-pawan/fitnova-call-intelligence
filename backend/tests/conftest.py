import os
import shutil
import pytest
from backend.app.core.config import settings

@pytest.fixture(autouse=True)
def clean_test_storage():
    """
    Cleans up cached storage files in test execution directories before running tests.
    """
    storage_dirs = [
        "./storage/transcripts",
        "./storage/conversations",
        "./storage/analysis",
        "./storage/processed"
    ]
    for folder in storage_dirs:
        if os.path.exists(folder):
            for item in os.listdir(folder):
                if item == ".gitkeep":
                    continue
                path = os.path.join(folder, item)
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except Exception:
                    pass
    yield

@pytest.fixture(autouse=True)
def mock_gemini_settings():
    """
    Globally mocks settings for all pytest runs to bypass live external Gemini API.
    """
    original_key = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = "mock_key_for_development"
    yield
    settings.GEMINI_API_KEY = original_key
