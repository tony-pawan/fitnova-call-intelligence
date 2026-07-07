from pydantic import Field  # pyrefly: ignore [missing-import]
from backend.app.schemas.common import BaseSchema, TimestampSchema

class TranscriptSegmentBase(BaseSchema):
    call_id: int
    speaker: str = Field(..., min_length=1, max_length=255, description="Name or identifier of the speaker")
    start_time: float = Field(..., ge=0.0, description="Segment start offset in seconds")
    end_time: float = Field(..., ge=0.0, description="Segment end offset in seconds")
    text: str = Field(..., min_length=1, description="Transcribed text content")

class TranscriptSegmentCreate(TranscriptSegmentBase):
    pass

class TranscriptSegment(TranscriptSegmentBase, TimestampSchema):
    id: int
