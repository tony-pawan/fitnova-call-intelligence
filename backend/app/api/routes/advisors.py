from typing import List
from fastapi import APIRouter, Depends  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.database.session import get_db
from backend.app.services.organization_service import OrganizationService
from backend.app.schemas.advisor import Advisor

router = APIRouter(prefix="/advisors", tags=["Advisors"])

@router.get("", response_model=List[Advisor])
def get_advisors(db: Session = Depends(get_db)):
    """
    Retrieves all sales advisors in the database.
    """
    return OrganizationService.list_advisors(db)
