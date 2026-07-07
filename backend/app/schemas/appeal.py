from pydantic import Field  # pyrefly: ignore [missing-import]
from backend.app.models.appeal import AppealStatus
from backend.app.schemas.common import BaseSchema, TimestampSchema

class AppealBase(BaseSchema):
    issue_tag_id: int
    advisor_id: int
    reason: str = Field(..., min_length=1, description="Advisor's justification for appeal")
    status: AppealStatus = Field(default=AppealStatus.Pending, description="Approval status of the appeal")

class AppealCreate(AppealBase):
    pass

class AppealUpdate(BaseSchema):
    status: AppealStatus = Field(..., description="Approval status update")

class Appeal(AppealBase, TimestampSchema):
    id: int
