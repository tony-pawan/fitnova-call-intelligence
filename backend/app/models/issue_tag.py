from datetime import datetime
import enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Enum, func  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship  # pyrefly: ignore [missing-import]
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.analysis import CallAnalysis

class Severity(str, enum.Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"
    Critical = "Critical"

class IssueTag(Base):
    __tablename__ = "issue_tags"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("call_analyses.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity_enum", native_enum=False),
        nullable=False,
        index=True
    )
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Review columns
    review_status: Mapped[str] = mapped_column(String(100), nullable=False, default="Pending", index=True)
    reviewer_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # New AI evidence audit columns
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_segments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    analysis: Mapped["CallAnalysis"] = relationship("CallAnalysis", back_populates="issue_tags")
