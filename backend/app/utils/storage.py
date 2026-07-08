import os
import uuid
from datetime import datetime
from backend.app.core.logging import get_logger

logger = get_logger("UPLOAD")

# --- Storage Provider Abstractions for S3/Blob Cloud Support ---
class BaseStorageProvider:
    """
    Common interface for file system backend operations.
    Allows local disk to be swapped with S3/GCS/Azure Blob Storage in the future.
    """
    def save(self, content: bytes, path: str) -> None:
        raise NotImplementedError()
        
    def load(self, path: str) -> bytes:
        raise NotImplementedError()
        
    def delete(self, path: str) -> None:
        raise NotImplementedError()

class LocalStorageProvider(BaseStorageProvider):
    """
    Standard Local File System Storage Provider.
    """
    def save(self, content: bytes, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)

    def load(self, path: str) -> bytes:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found on local disk: {path}")
        with open(path, "rb") as f:
            return f.read()

    def delete(self, path: str) -> None:
        if os.path.exists(path):
            os.remove(path)

# --- Extensible Cloud Provider Stubs (For demonstration) ---
class S3StorageProvider(BaseStorageProvider):
    """AWS S3 Extensible Storage Provider Stub."""
    def save(self, content: bytes, path: str) -> None:
        raise NotImplementedError("S3StorageProvider is a stub. Configure Boto3 clients to implement.")
        
    def load(self, path: str) -> bytes:
        raise NotImplementedError()
        
    def delete(self, path: str) -> None:
        raise NotImplementedError()

class GCSStorageProvider(BaseStorageProvider):
    """Google Cloud Storage Extensible Storage Provider Stub."""
    def save(self, content: bytes, path: str) -> None:
        raise NotImplementedError("GCSStorageProvider is a stub. Configure GCS storage clients to implement.")
        
    def load(self, path: str) -> bytes:
        raise NotImplementedError()
        
    def delete(self, path: str) -> None:
        raise NotImplementedError()

class AzureBlobStorageProvider(BaseStorageProvider):
    """Azure Blob Storage Extensible Storage Provider Stub."""
    def save(self, content: bytes, path: str) -> None:
        raise NotImplementedError("AzureBlobStorageProvider is a stub. Configure Azure storage clients to implement.")
        
    def load(self, path: str) -> bytes:
        raise NotImplementedError()
        
    def delete(self, path: str) -> None:
        raise NotImplementedError()

# --- Refactored StorageManager ---
class StorageManager:
    def __init__(self, base_dir: str = "./storage/audio", provider: BaseStorageProvider = None) -> None:
        self.base_dir = base_dir
        self.provider = provider or LocalStorageProvider()

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
        return os.path.normpath(os.path.join(self.base_dir, year, month)).replace("\\", "/")

    def save_file(self, file_content: bytes, original_filename: str) -> dict:
        """
        Saves the file content via the configured storage provider.
        Returns a metadata dictionary detailing pathing and size metrics.
        """
        logger.info("[UPLOAD] Saving file via storage provider")
        target_dir = self.get_storage_path()
        stored_filename = self.generate_filename(original_filename)
        full_path = os.path.normpath(os.path.join(target_dir, stored_filename)).replace("\\", "/")

        self.provider.save(file_content, full_path)
        file_size = len(file_content)

        return {
            "stored_filename": stored_filename,
            "audio_path": full_path,
            "file_size_bytes": file_size
        }

    def read_file(self, path: str) -> bytes:
        """
        Reads files from storage.
        """
        return self.provider.load(path)

    def delete_file(self, path: str) -> None:
        """
        Removes files from storage.
        """
        self.provider.delete(path)
