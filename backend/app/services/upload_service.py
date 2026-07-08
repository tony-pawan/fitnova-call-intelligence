import os
from typing import Optional
from fastapi import UploadFile, HTTPException, BackgroundTasks  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from backend.app.models.call import Call, CallStatus
from backend.app.utils.storage import StorageManager
from backend.app.utils.metadata import extract_audio_metadata
from backend.app.core.logging import get_logger

logger = get_logger("UPLOAD")

class UploadService:
    def __init__(self, storage_manager: StorageManager = None) -> None:
        self.storage_manager = storage_manager or StorageManager()

    def upload_call(
        self,
        db: Session,
        audio_file: UploadFile,
        background_tasks: BackgroundTasks,
        organization_id: Optional[int] = None,
        team_id: Optional[int] = None,
        advisor_id: Optional[int] = None,
        source_id: Optional[int] = None
    ) -> Call:
        """
        Coordinates the complete end-to-end upload sequence:
        Validation ➔ Save to Disk ➔ Metadata Extraction ➔ CallInput DTO Mapping ➔ Database Persistence ➔ Trigger Pipeline
        """
        logger.info("[UPLOAD] Upload request received")

        # 1. Validate file exists
        if not audio_file or not audio_file.filename:
            logger.error("[UPLOAD] Missing file in request")
            raise HTTPException(status_code=400, detail="Missing audio file in request")

        # 3. Validate supported extension (.wav, .mp3, .m4a)
        filename = audio_file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in [".wav", ".mp3", ".m4a"]:
            logger.error(f"[UPLOAD] Unsupported extension: {ext}")
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type extension '{ext}'. Only .wav, .mp3, and .m4a files are accepted."
            )

        # 4. Validate maximum file size <= 100 MB
        try:
            content = audio_file.file.read()
        except Exception as e:
            logger.error(f"[UPLOAD] Failed to read uploaded file: {e}")
            raise HTTPException(status_code=400, detail="Could not read uploaded file content")

        file_size = len(content)
        max_size_bytes = 100 * 1024 * 1024
        if file_size > max_size_bytes:
            logger.error(f"[UPLOAD] Oversized file: {file_size} bytes")
            raise HTTPException(
                status_code=400, 
                detail=f"Uploaded file size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum limit of 100 MB"
            )

        logger.info("[UPLOAD] Validation successful")

        # 5. Save file using the StorageManager
        try:
            storage_meta = self.storage_manager.save_file(content, filename)
        except Exception as e:
            logger.error(f"[UPLOAD] Storage failure: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded audio file to disk storage")

        # 6. Extract duration using mutagen
        audio_path = storage_meta["audio_path"]
        metadata = extract_audio_metadata(audio_path)

        # 7. Map to canonical CallInput DTO via ManualUploadConnector
        from backend.app.ai.ingestion.connector import ManualUploadConnector
        connector = ManualUploadConnector()
        call_input = connector.ingest({
            "audio_path": audio_path,
            "original_filename": filename,
            "mime_type": audio_file.content_type or f"audio/{ext.lstrip('.')}",
            "duration": metadata["duration_seconds"],
            "organization_id": organization_id,
            "team_id": team_id,
            "advisor_id": advisor_id,
            "source_id": source_id
        })

        # 8. Create database call record in PostgreSQL using canonical CallInput
        logger.info("[UPLOAD] Database record created via CallInput DTO")
        try:
            db_call = Call(
                original_filename=call_input.original_filename,
                stored_filename=storage_meta["stored_filename"],
                audio_path=call_input.audio_path,
                mime_type=call_input.mime_type,
                file_size_bytes=storage_meta["file_size_bytes"],
                duration_seconds=call_input.duration,
                status=CallStatus.Uploaded,
                language=call_input.language,
                organization_id=call_input.organization_id,
                team_id=call_input.team_id,
                advisor_id=call_input.advisor_id,
                source_id=call_input.source_id
            )
            db.add(db_call)
            db.commit()
            db.refresh(db_call)
        except Exception as e:
            logger.error(f"[UPLOAD] Database failure: {e}")
            db.rollback()
            self.storage_manager.delete_file(audio_path)
            raise HTTPException(status_code=500, detail="Failed to persist call recording entry to database")

        logger.info("[UPLOAD] Upload completed")

        # 9. Trigger asynchronous processing pipeline
        from backend.app.pipeline.background import trigger_call_processing
        trigger_call_processing(db_call.id, background_tasks)

        return db_call
