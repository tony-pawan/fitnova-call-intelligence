from typing import List
from pydantic import BaseModel, Field  # pyrefly: ignore [missing-import]

class ConversationSegment(BaseModel):
    """
    Data Transfer Object (DTO) representing a single speaker turn/segment.
    """
    speaker: str = Field(..., description="Advisor, Customer, or Speaker X label")
    start: float = Field(..., description="Start offset in seconds")
    end: float = Field(..., description="End offset in seconds")
    text: str = Field(..., description="Transcribed speech content")

class ConversationResult(BaseModel):
    """
    Data Transfer Object (DTO) carrying the full reconstructed conversation.
    """
    language: str = Field(..., description="Language of the conversation")
    duration: float = Field(..., description="Total duration of the audio in seconds")
    segments: List[ConversationSegment] = Field(..., description="Reconstructed sequential conversation segments")
