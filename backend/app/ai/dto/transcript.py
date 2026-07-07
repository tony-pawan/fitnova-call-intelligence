from typing import List, Optional
from pydantic import BaseModel, Field  # pyrefly: ignore [missing-import]

class TranscriptSegment(BaseModel):
    """
    Data Transfer Object (DTO) representing a single transcription segment.
    """
    start: float = Field(..., description="Start offset in seconds")
    end: float = Field(..., description="End offset in seconds")
    text: str = Field(..., description="Transcribed text statement content")
    confidence: Optional[float] = Field(default=None, description="Average confidence score of the segment")

class TranscriptResult(BaseModel):
    """
    Data Transfer Object (DTO) carrying the full transcription results payload.
    """
    language: str = Field(..., description="Detected text language identifier")
    duration: float = Field(..., description="Full duration in seconds")
    segments: List[TranscriptSegment] = Field(..., description="List of individual text segments")
