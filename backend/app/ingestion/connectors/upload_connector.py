import os
import shutil
from typing import List, Dict, Any
from backend.app.ingestion.base import SourceConnector
from backend.app.ingestion.dto import AudioInput
from backend.app.core.logging import get_logger

logger = get_logger("INGESTION")

class UploadConnector(SourceConnector):
    """
    Ingestion connector for directly uploaded audio recordings.
    """
    def __init__(self, filename: str, temp_path: str, size_bytes: int, metadata: Dict[str, Any] = None):
        self.filename = filename
        self.temp_path = temp_path
        self.size_bytes = size_bytes
        self.meta = metadata or {}

    def connect(self) -> bool:
        return True

    def validate(self) -> bool:
        if not os.path.exists(self.temp_path):
            logger.error(f"Uploaded temporary file not found at: {self.temp_path}")
            return False
        
        ext = os.path.splitext(self.filename)[1].lower()
        if ext not in [".wav", ".mp3", ".m4a", ".aac"]:
            logger.error(f"Unsupported file format: {ext}")
            return False
            
        return True

    def fetch(self) -> List[AudioInput]:
        if not self.validate():
            raise ValueError("Pre-ingestion validation failed for uploaded recording")
            
        # Determine MIME type
        ext = os.path.splitext(self.filename)[1].lower()
        mime_type = "audio/mpeg" if ext == ".mp3" else (
            "audio/wav" if ext == ".wav" else f"audio/{ext[1:]}"
        )
        
        # Build normalized input DTO
        audio_input = self.normalize({
            "audio_path": self.temp_path,
            "original_filename": self.filename,
            "mime_type": mime_type,
            "file_size": self.size_bytes,
            "metadata": self.meta
        })
        
        return [audio_input]

    def normalize(self, raw_data: dict) -> AudioInput:
        meta = raw_data.get("metadata", {})
        return AudioInput(
            source="Upload",
            vendor=meta.get("vendor", "Direct Upload"),
            audio_path=raw_data["audio_path"],
            original_filename=raw_data["original_filename"],
            mime_type=raw_data["mime_type"],
            duration=0.0,  # Pipeline will calculate duration using soundfile/wave
            call_time=meta.get("call_time"),
            external_call_id=meta.get("external_call_id"),
            customer_name=meta.get("customer_name"),
            advisor_name=meta.get("advisor_name"),
            metadata=meta
        )
