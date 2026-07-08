from pydantic import BaseModel, Field  # pyrefly: ignore [missing-import]
from typing import Optional, Dict, Any

class AudioInput(BaseModel):
    """
    Unified Data Transfer Object representing a standardized incoming call ingestion payload.
    """
    source: str = Field(..., description="Ingestion source type (e.g., Upload, Folder, CRM, API, Telephony, Dialer)")
    vendor: str = Field(..., description="Specific vendor or connector name (e.g., Twilio, Salesforce, Local)")
    audio_path: str = Field(..., description="Absolute local filesystem path to the audio recording")
    original_filename: str = Field(..., description="Base filename of the recording")
    mime_type: str = Field(..., description="MIME type of the audio file")
    duration: float = Field(default=0.0, description="Recording duration in seconds")
    call_time: Optional[str] = Field(default=None, description="ISO 8601 timestamp of the call execution")
    external_call_id: Optional[str] = Field(default=None, description="External vendor unique call identifier")
    customer_name: Optional[str] = Field(default=None, description="Name of the customer client")
    advisor_name: Optional[str] = Field(default=None, description="Name of the advisor agent")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Key-value custom vendor attributes")
