import os
import uuid
from datetime import datetime
from backend.app.core.logging import get_logger

logger = get_logger("UPLOAD")

class StorageManager:
    def __init__(self, base_dir: str = "./storage/audio") -> None:
        self.base_dir = base_dir

    def generate_filename(self, original_filename: str) -> str:
        """
        Generates a unique UUID-based filename preserving the original extension.
        """
        logger.info("[UPLOAD] Generating UUID filename")
        ext = os.path.splitext(original_filename)[1].lower()
        return f"{uuid.uuid4()}{ext}"

    def get_storage_path(self) -> str:
        """
        Returns the relative directory structure: base_dir/YYYY/MM/
        """
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        return os.path.join(self.base_dir, year, month)

    def save_file(self, file_content: bytes, original_filename: str) -> dict:
        """
        Saves the file content to disk, creating directory hierarchies if needed.
        Returns a metadata dictionary detailing pathing and size metrics.
        """
        logger.info("[UPLOAD] Saving file")
        target_dir = self.get_storage_path()
        os.makedirs(target_dir, exist_ok=True)

        stored_filename = self.generate_filename(original_filename)
        full_path = os.path.join(target_dir, stored_filename)

        with open(full_path, "wb") as f:
            f.write(file_content)

        file_size = len(file_content)
        
        # Convert path delimiters to forward slashes for database consistency
        normalized_path = os.path.normpath(full_path).replace("\\", "/")

        return {
            "stored_filename": stored_filename,
            "audio_path": normalized_path,
            "file_size_bytes": file_size
        }
