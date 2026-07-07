from datetime import datetime
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.transcript import TranscriptSegment as TranscriptSegmentModel
from backend.app.ai.dto.conversation import ConversationResult
from backend.app.utils.json_storage import save_json
from backend.app.core.logging import get_logger

logger = get_logger("DIARIZATION")

class ConversationStorageService:
    @staticmethod
    def persist_conversation(db: Session, call_id: int, result: ConversationResult) -> bool:
        """
        Updates the database transcript segment speaker labels and writes the complete
        versioned JSON conversation history to storage/conversations/call_<call_id>.json.
        """
        logger.info(f"Persisting conversation details for Call ID {call_id}")

        # 1. Update TranscriptSegment speaker values in PostgreSQL
        try:
            db_segments = db.query(TranscriptSegmentModel).filter(
                TranscriptSegmentModel.call_id == call_id
            ).order_by(TranscriptSegmentModel.start_time.asc()).all()
            
            dto_segments = sorted(result.segments, key=lambda s: s.start)
            
            if len(db_segments) == len(dto_segments):
                for db_seg, dto_seg in zip(db_segments, dto_segments):
                    db_seg.speaker = dto_seg.speaker
            else:
                logger.warning(f"Segment count mismatch between DB ({len(db_segments)}) and DTO ({len(dto_segments)}). Falling back to timestamp matching.")
                for db_seg in db_segments:
                    for dto_seg in dto_segments:
                        if abs(db_seg.start_time - dto_seg.start) < 0.02:
                            db_seg.speaker = dto_seg.speaker
                            break
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update database transcript segments speakers for Call ID {call_id}: {e}")
            raise

        # 2. Persist versioned JSON conversation metadata
        json_data = {
            "version": "1.0",
            "generated_at": datetime.now().isoformat(),
            "language": result.language,
            "duration": result.duration,
            "segments": [
                {
                    "speaker": s.speaker,
                    "start": s.start,
                    "end": s.end,
                    "text": s.text
                } for s in result.segments
            ]
        }
        
        file_path = f"./storage/conversations/call_{call_id}.json"
        saved = save_json(file_path, json_data)
        if saved:
            logger.info("Conversation stored successfully")
        else:
            logger.error(f"Failed to write JSON conversation file for Call ID {call_id}")
            raise RuntimeError("Filesystem save failure")
            
        return saved
