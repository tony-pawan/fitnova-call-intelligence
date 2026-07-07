from typing import List
from fastapi import APIRouter, Depends, HTTPException, status  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.database.session import get_db
from backend.app.models.appeal import Appeal as AppealModel, AppealStatus
from backend.app.schemas.appeal import Appeal as AppealSchema, AppealCreate, AppealUpdate
from backend.app.services.appeal_service import AppealService
from backend.app.core.logging import get_logger

logger = get_logger("APPEAL")
router = APIRouter(prefix="/appeals", tags=["appeals"])

@router.post("", response_model=AppealSchema, status_code=status.HTTP_201_CREATED)
def submit_appeal(appeal_in: AppealCreate, db: Session = Depends(get_db)):
    """
    Submits a new appeal disputing a flagged issue tag. Prevents duplicates.
    """
    # Duplicate prevention check
    existing = db.query(AppealModel).filter(AppealModel.issue_tag_id == appeal_in.issue_tag_id).first()
    if existing:
        logger.warning(f"[APPEAL] Duplicate appeal attempt for IssueTag ID {appeal_in.issue_tag_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This issue tag has already been appealed."
        )
        
    db_appeal = AppealService.submit_appeal(db, appeal_in)
    logger.info(f"[APPEAL] Appeal submitted: Appeal ID {db_appeal.id} against IssueTag ID {db_appeal.issue_tag_id}")
    return db_appeal

@router.get("", response_model=List[AppealSchema])
def list_appeals(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Lists all submitted appeal records.
    """
    return AppealService.list_appeals(db, skip=skip, limit=limit)

@router.get("/{appeal_id}", response_model=AppealSchema)
def view_appeal(appeal_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a single appeal record by its ID.
    """
    appeal = AppealService.get_appeal(db, appeal_id)
    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appeal with ID {appeal_id} not found."
        )
    return appeal

@router.patch("/{appeal_id}", response_model=AppealSchema)
def update_appeal_status(appeal_id: int, status_update: AppealUpdate, db: Session = Depends(get_db)):
    """
    Resolves an appeal by updating its approval status (Pending -> Approved or Rejected).
    """
    appeal = AppealService.get_appeal(db, appeal_id)
    if not appeal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appeal with ID {appeal_id} not found."
        )
        
    updated_appeal = AppealService.update_appeal_status(db, appeal_id, status_update.status)
    logger.info(f"[APPEAL] Appeal {status_update.status.lower()}: Appeal ID {appeal_id}")
    return updated_appeal
