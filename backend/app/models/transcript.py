from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, func  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship  # pyrefly: ignore [missing-import]
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.call import Call

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    call_id: Mapped[int] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    # Speaker column must be nullable to support initial transcription before speaker diarization occurs
    speaker: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(), 
        onupdate=func.now()
    )

    # Relationships
    call: Mapped["Call"] = relationship(back_populates="transcript_segments")
