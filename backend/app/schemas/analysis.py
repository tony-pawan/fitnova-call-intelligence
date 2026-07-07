from pydantic import Field  # pyrefly: ignore [missing-import]
from backend.app.schemas.common import BaseSchema, TimestampSchema

class CallAnalysisBase(BaseSchema):
    call_id: int
    overall_score: int = Field(..., ge=0, le=100, description="Overall quality score from 0 to 100")
    summary: str = Field(..., min_length=1, description="Structured call analytics summary")
    recommendation: str = Field(..., min_length=1, description="Advisor feedback recommendation")

class CallAnalysisCreate(CallAnalysisBase):
    pass

class CallAnalysis(CallAnalysisBase, TimestampSchema):
    id: int
