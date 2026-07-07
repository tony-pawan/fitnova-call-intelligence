from datetime import datetime
import enum
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, ForeignKey, Text, Enum, func  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship  # pyrefly: ignore [missing-import]
from backend.app.database.base import Base

if TYPE_CHECKING:
    from backend.app.models.issue_tag import IssueTag
    from backend.app.models.advisor import Advisor

class AppealStatus(str, enum.Enum):
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"

class Appeal(Base):
    __tablename__ = "appeals"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    issue_tag_id: Mapped[int] = mapped_column(
        ForeignKey("issue_tags.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    advisor_id: Mapped[int] = mapped_column(
        ForeignKey("advisors.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[AppealStatus] = mapped_column(
        Enum(AppealStatus, name="appeal_status_enum", native_enum=False),
        default=AppealStatus.Pending,
        nullable=False,
        index=True
    )
    
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
    issue_tag: Mapped["IssueTag"] = relationship("IssueTag", back_populates="appeals")
    advisor: Mapped["Advisor"] = relationship("Advisor", back_populates="appeals")
