from pydantic import Field  # pyrefly: ignore [missing-import]
from backend.app.models.issue_tag import Severity
from backend.app.schemas.common import BaseSchema, TimestampSchema

class IssueTagBase(BaseSchema):
    analysis_id: int
    tag: str = Field(..., min_length=1, max_length=100, description="Short issue description identifier")
    severity: Severity = Field(..., description="Issue severity tag")
    timestamp: float = Field(..., ge=0.0, description="Offset time in seconds where issue quote occurred")
    quote: str = Field(..., min_length=1, description="Direct quote from advisor/transcript")
    reason: str = Field(..., min_length=1, description="Root-cause explanation for the flag")

class IssueTagCreate(IssueTagBase):
    pass

class IssueTag(IssueTagBase, TimestampSchema):
    id: int
