from typing import Optional, List
from pydantic import Field  # pyrefly: ignore [missing-import]
from backend.app.models.call import CallStatus
from backend.app.schemas.common import BaseSchema, TimestampSchema

class CallBase(BaseSchema):
    original_filename: str = Field(..., min_length=1, max_length=255)
    stored_filename: str = Field(..., min_length=1, max_length=255)
    audio_path: str = Field(..., min_length=1, max_length=1024, description="File path to the audio file")
    mime_type: str = Field(..., min_length=1, max_length=100)
    file_size_bytes: int = Field(..., ge=0)
    status: CallStatus = Field(default=CallStatus.Uploaded)
    duration_seconds: float = Field(default=0.0, ge=0.0, description="Duration in seconds (must be non-negative)")
    language: Optional[str] = Field(default="en", min_length=1, max_length=50)

class CallCreate(CallBase):
    pass

class CallUpdate(BaseSchema):
    original_filename: Optional[str] = Field(None, min_length=1, max_length=255)
    stored_filename: Optional[str] = Field(None, min_length=1, max_length=255)
    audio_path: Optional[str] = Field(None, min_length=1, max_length=1024)
    mime_type: Optional[str] = Field(None, min_length=1, max_length=100)
    file_size_bytes: Optional[int] = Field(None, ge=0)
    status: Optional[CallStatus] = Field(None)
    duration_seconds: Optional[float] = Field(None, ge=0.0)
    language: Optional[str] = Field(None, min_length=1, max_length=50)

class Call(CallBase, TimestampSchema):
    id: int
    timeline: Optional[List[dict]] = Field(default=None, description="Timeline of processing events")
