from typing import List, Optional
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.models.appeal import Appeal, AppealStatus
from backend.app.schemas.appeal import AppealCreate
from backend.app.core.logging import get_logger

logger = get_logger("DATABASE")

class AppealService:
    @staticmethod
    def get_appeal(db: Session, appeal_id: int) -> Optional[Appeal]:
        """
        Retrieves a single Appeal record by its ID.
        """
        return db.query(Appeal).filter(Appeal.id == appeal_id).first()

    @staticmethod
    def submit_appeal(db: Session, appeal: AppealCreate) -> Appeal:
        """
        Creates a new Appeal record against a flagged issue.
        """
        logger.info(f"DB Operation: Advisor {appeal.advisor_id} is appealing issue tag: {appeal.issue_tag_id}")
        db_appeal = Appeal(
            issue_tag_id=appeal.issue_tag_id,
            advisor_id=appeal.advisor_id,
            reason=appeal.reason,
            status=appeal.status
        )
        db.add(db_appeal)
        db.commit()
        db.refresh(db_appeal)
        return db_appeal

    @staticmethod
    def update_appeal_status(db: Session, appeal_id: int, status: AppealStatus) -> Optional[Appeal]:
        """
        Updates the status of an appeal (e.g. Pending -> Approved / Rejected).
        """
        logger.info(f"DB Operation: Transitioning Appeal ID {appeal_id} to status: {status}")
        db_appeal = db.query(Appeal).filter(Appeal.id == appeal_id).first()
        if db_appeal:
            db_appeal.status = status
            db.commit()
            db.refresh(db_appeal)
        return db_appeal

    @staticmethod
    def list_appeals(db: Session, skip: int = 0, limit: int = 100) -> List[Appeal]:
        """
        Lists all Appeal records.
        """
        return db.query(Appeal).offset(skip).limit(limit).all()
