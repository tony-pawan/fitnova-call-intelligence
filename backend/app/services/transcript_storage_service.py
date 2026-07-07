from datetime import datetime
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.transcript import TranscriptSegment as TranscriptSegmentModel
from backend.app.ai.dto.transcript import TranscriptResult
from backend.app.utils.json_storage import save_json
from backend.app.core.logging import get_logger

logger = get_logger("TRANSCRIPTION")

class TranscriptStorageService:
    @staticmethod
    def persist_transcript(db: Session, call_id: int, result: TranscriptResult) -> bool:
        """
        Stores transcript segments in PostgreSQL and saves the complete versioned JSON transcript
        to the local filesystem under storage/transcripts/call_<call_id>.json.
        """
        logger.info(f"Persisting transcript details for Call ID {call_id}")

        # 1. Save segments to PostgreSQL
        try:
            # Delete any existing segments for this call first to ensure idempotency and prevent duplicates
            db.query(TranscriptSegmentModel).filter(TranscriptSegmentModel.call_id == call_id).delete()
            
            for segment in result.segments:
                db_segment = TranscriptSegmentModel(
                    call_id=call_id,
                    start_time=segment.start,
                    end_time=segment.end,
                    text=segment.text,
                    speaker=None  # Speaker attribution will be run during diarization stage
                )
                db.add(db_segment)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist transcript segments in DB for Call ID {call_id}: {e}")
            raise

        # 2. Save JSON file to filesystem with versioned metadata
        json_data = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "language": result.language,
            "duration": result.duration,
            "segments": [
                {
                    "start": s.start,
                    "end": s.end,
                    "text": s.text,
                    "confidence": s.confidence
                } for s in result.segments
            ]
        }
        
        file_path = f"./storage/transcripts/call_{call_id}.json"
        saved = save_json(file_path, json_data)
        if saved:
            logger.info("Transcript stored successfully")
        else:
            logger.error(f"Failed to write JSON transcript file for Call ID {call_id}")
            raise RuntimeError("Filesystem save failure")
            
        return saved
