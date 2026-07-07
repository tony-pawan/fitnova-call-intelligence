from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import Integer, DateTime, ForeignKey, Text, func  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship  # pyrefly: ignore [missing-import]
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.call import Call
    from backend.app.models.issue_tag import IssueTag

class CallAnalysis(Base):
    __tablename__ = "call_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    call_id: Mapped[int] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True,
        index=True
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    
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
    call: Mapped["Call"] = relationship("Call", back_populates="analysis")
    
    issue_tags: Mapped[List["IssueTag"]] = relationship(
        "IssueTag", 
        back_populates="analysis", 
        cascade="all, delete-orphan"
    )
