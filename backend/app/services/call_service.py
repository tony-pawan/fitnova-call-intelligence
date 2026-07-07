from typing import List, Optional
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.call import Call, CallStatus
from backend.app.models.transcript import TranscriptSegment
from backend.app.schemas.call import CallCreate
from backend.app.schemas.transcript import TranscriptSegmentCreate
from backend.app.core.logging import get_logger

logger = get_logger("DATABASE")

class CallService:
    @staticmethod
    def get_call(db: Session, call_id: int) -> Optional[Call]:
        """
        Retrieves a single Call record by ID.
        """
        return db.query(Call).filter(Call.id == call_id).first()

    @staticmethod
    def create_call(db: Session, call: CallCreate) -> Call:
        """
        Creates a new Call record.
        """
        logger.info(f"DB Operation: Ingesting call record for advisor ID: {call.advisor_id}")
        db_call = Call(
            advisor_id=call.advisor_id,
            audio_path=call.audio_path,
            status=call.status,
            duration_seconds=call.duration_seconds,
            language=call.language
        )
        db.add(db_call)
        db.commit()
        db.refresh(db_call)
        return db_call

    @staticmethod
    def update_call_status(db: Session, call_id: int, status: CallStatus) -> Optional[Call]:
        """
        Updates the Call processing status (e.g. Uploaded -> Queued -> Processing -> Completed).
        """
        logger.info(f"DB Operation: Transitioning Call ID {call_id} to status: {status}")
        db_call = db.query(Call).filter(Call.id == call_id).first()
        if db_call:
            db_call.status = status
            db.commit()
            db.refresh(db_call)
        return db_call

    @staticmethod
    def list_calls(db: Session, skip: int = 0, limit: int = 100) -> List[Call]:
        """
        Lists all Call records.
        """
        return db.query(Call).offset(skip).limit(limit).all()

    @staticmethod
    def create_transcript_segment(db: Session, segment: TranscriptSegmentCreate) -> TranscriptSegment:
        """
        Creates a new TranscriptSegment record linked to a Call.
        """
        db_segment = TranscriptSegment(
            call_id=segment.call_id,
            speaker=segment.speaker,
            start_time=segment.start_time,
            end_time=segment.end_time,
            text=segment.text
        )
        db.add(db_segment)
        db.commit()
        db.refresh(db_segment)
        return db_segment

    @staticmethod
    def get_transcript_segments(db: Session, call_id: int) -> List[TranscriptSegment]:
        """
        Retrieves all TranscriptSegments for a call, sorted by start_time.
        """
        return db.query(TranscriptSegment).filter(TranscriptSegment.call_id == call_id).order_by(TranscriptSegment.start_time).all()
