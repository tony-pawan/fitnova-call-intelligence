from datetime import datetime
import enum
from typing import List, TYPE_CHECKING, Optional
from sqlalchemy import String, DateTime, ForeignKey, Integer, Float, Enum, func, Text  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship  # pyrefly: ignore [missing-import]
from backend.app.database.base import Base  # pyrefly: ignore [missing-import]

if TYPE_CHECKING:
    from backend.app.models.transcript import TranscriptSegment
    from backend.app.models.analysis import CallAnalysis
    from backend.app.models.advisor import Advisor
    from backend.app.models.ingestion_source import IngestionSource

class CallStatus(str, enum.Enum):
    Uploaded = "Uploaded"
    Queued = "Queued"
    Processing = "Processing"
    Completed = "Completed"
    Failed = "Failed"

class Call(Base):
    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    audio_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CallStatus] = mapped_column(
        Enum(CallStatus, name="call_status_enum", native_enum=False),
        default=CallStatus.Uploaded,
        nullable=False,
        index=True
    )
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    language: Mapped[str] = mapped_column(String(50), nullable=True, default="en")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Ingestion Source Abstraction columns
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="Upload", index=True)
    vendor: Mapped[str] = mapped_column(String(100), nullable=False, default="Direct", index=True)
    external_call_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    advisor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    ingestion_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # New Organization hierarchy foreign keys
    organization_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True)
    advisor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("advisors.id", ondelete="SET NULL"), nullable=True, index=True)
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ingestion_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )

    # Relationships
    transcript_segments: Mapped[List["TranscriptSegment"]] = relationship(
        "TranscriptSegment", 
        back_populates="call", 
        cascade="all, delete-orphan"
    )
    
    analysis: Mapped["CallAnalysis"] = relationship(
        "CallAnalysis", 
        back_populates="call", 
        cascade="all, delete-orphan",
        uselist=False
    )

    advisor: Mapped[Optional["Advisor"]] = relationship("Advisor", back_populates="calls")
    ingestion_source: Mapped[Optional["IngestionSource"]] = relationship("IngestionSource", back_populates="calls")
