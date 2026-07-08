import os
from typing import List, Dict, Any
from backend.app.ingestion.base import SourceConnector
from backend.app.ingestion.dto import AudioInput
from backend.app.core.logging import get_logger

logger = get_logger("INGESTION")

class APIConnector(SourceConnector):
    """
    Ingestion connector for REST API programmatical call submissions.
    """
    def __init__(self, filename: str, temp_path: str, external_call_id: str, metadata: Dict[str, Any] = None):
        self.filename = filename
        self.temp_path = temp_path
        self.external_call_id = external_call_id
        self.meta = metadata or {}

    def connect(self) -> bool:
        return True

    def validate(self) -> bool:
        if not os.path.exists(self.temp_path):
            logger.error(f"API submitted audio file not found at: {self.temp_path}")
            return False
            
        ext = os.path.splitext(self.filename)[1].lower()
        if ext not in [".wav", ".mp3", ".m4a", ".aac"]:
            logger.error(f"Unsupported REST API audio format: {ext}")
            return False
            
        return True

    def fetch(self) -> List[AudioInput]:
        if not self.validate():
            raise ValueError("REST API call submission validation failed")

        ext = os.path.splitext(self.filename)[1].lower()
        mime_type = "audio/mpeg" if ext == ".mp3" else (
            "audio/wav" if ext == ".wav" else f"audio/{ext[1:]}"
        )

        audio_input = self.normalize({
            "audio_path": self.temp_path,
            "original_filename": self.filename,
            "mime_type": mime_type,
            "external_call_id": self.external_call_id,
            "metadata": self.meta
        })

        return [audio_input]

    def normalize(self, raw_data: dict) -> AudioInput:
        meta = raw_data.get("metadata", {})
        return AudioInput(
            source="API",
            vendor=meta.get("vendor", "REST API Endpoint"),
            audio_path=raw_data["audio_path"],
            original_filename=raw_data["original_filename"],
            mime_type=raw_data["mime_type"],
            duration=0.0,
            call_time=meta.get("call_time"),
            external_call_id=raw_data["external_call_id"],
            customer_name=meta.get("customer_name"),
            advisor_name=meta.get("advisor_name"),
            metadata=meta
        )
