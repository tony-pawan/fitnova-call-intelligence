from pydantic import BaseModel, Field  # pyrefly: ignore [missing-import]
from typing import Optional, Dict, Any
from datetime import datetime

class CallInput(BaseModel):
    """
    Canonical Data Transfer Object returned by all source-agnostic connectors
    before entering the processing pipeline.
    """
    call_id: Optional[int] = None
    organization_id: Optional[int] = None
    team_id: Optional[int] = None
    advisor_id: Optional[int] = None
    source_id: Optional[int] = None
    audio_path: str
    original_filename: str
    mime_type: str
    duration: float = 0.0
    recorded_at: datetime = Field(default_factory=datetime.now)
    language: Optional[str] = "en"
    
    # Ingestion origin and connector fields (for backwards compatibility)
    source: str = Field(default="Upload", description="Ingestion source type")
    vendor: str = Field(default="Direct", description="Specific vendor or connector name")
    call_time: Optional[str] = Field(default=None, description="ISO timestamp")
    external_call_id: Optional[str] = Field(default=None, description="External vendor unique call identifier")
    customer_name: Optional[str] = Field(default=None, description="Name of the customer client")
    advisor_name: Optional[str] = Field(default=None, description="Name of the advisor agent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Key-value custom vendor attributes")

class AudioInput(CallInput):
    """
    Backwards compatibility subclass alias for existing ingestion connectors.
    """
    pass
