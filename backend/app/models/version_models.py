from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text, Float, func  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column  # pyrefly: ignore [missing-import]
from backend.app.database.base import Base

class TranscriptVersion(Base):
    __tablename__ = "transcript_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    call_id: Mapped[int] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

class ConversationVersion(Base):
    __tablename__ = "conversation_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    call_id: Mapped[int] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

class AnalysisVersion(Base):
    __tablename__ = "analysis_versions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    call_id: Mapped[int] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Review details override
    human_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    human_score_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    human_reviewer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )
