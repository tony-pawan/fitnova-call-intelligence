import os
import glob
from typing import List
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.ingestion.base import SourceConnector
from backend.app.ingestion.dto import AudioInput
from backend.app.models.call import Call
from backend.app.core.logging import get_logger

logger = get_logger("INGESTION")

class FolderConnector(SourceConnector):
    """
    Ingestion connector for scanning and importing call recordings from a local folder directory.
    """
    def __init__(self, folder_path: str, db: Session):
        self.folder_path = folder_path
        self.db = db

    def connect(self) -> bool:
        if not os.path.exists(self.folder_path) or not os.path.isdir(self.folder_path):
            logger.error(f"Target folder directory does not exist: {self.folder_path}")
            return False
        return True

    def validate(self) -> bool:
        return self.connect()

    def fetch(self) -> List[AudioInput]:
        if not self.validate():
            raise ValueError(f"Invalid watch directory: {self.folder_path}")

        # Scan for supported audio formats
        found_files = []
        for ext in ["*.wav", "*.mp3", "*.m4a", "*.aac"]:
            found_files.extend(glob.glob(os.path.join(self.folder_path, ext)))
            
        # Also handle lowercase/uppercase variations
        for ext in ["*.WAV", "*.MP3", "*.M4A", "*.AAC"]:
            found_files.extend(glob.glob(os.path.join(self.folder_path, ext)))

        # Deduplicate paths
        unique_paths = list(set(os.path.abspath(p) for p in found_files))
        logger.info(f"Discovered {len(unique_paths)} audio file(s) in watch directory.")

        # Get already ingested filenames from database to avoid duplicate processing
        existing_filenames = set(
            row[0] for row in self.db.query(Call.original_filename).filter(Call.source == "Folder").all()
        )

        new_inputs = []
        for file_path in unique_paths:
            filename = os.path.basename(file_path)
            
            # Skip duplicates
            if filename in existing_filenames:
                logger.debug(f"Skipping already ingested directory watch file: {filename}")
                continue

            # Determine MIME type
            ext = os.path.splitext(filename)[1].lower()
            mime_type = "audio/mpeg" if ext == ".mp3" else (
                "audio/wav" if ext == ".wav" else f"audio/{ext[1:]}"
            )

            audio_input = self.normalize({
                "audio_path": file_path,
                "original_filename": filename,
                "mime_type": mime_type
            })
            new_inputs.append(audio_input)

        logger.info(f"Adding {len(new_inputs)} new file(s) for watch directory ingestion.")
        return new_inputs

    def normalize(self, raw_data: dict) -> AudioInput:
        return AudioInput(
            source="Folder",
            vendor="Local Folder Scanner",
            audio_path=raw_data["audio_path"],
            original_filename=raw_data["original_filename"],
            mime_type=raw_data["mime_type"],
            duration=0.0,
            call_time=None,
            external_call_id=None,
            customer_name=None,
            advisor_name=None,
            metadata={"system_watch_path": self.folder_path}
        )
