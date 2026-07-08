import os
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel  # pyrefly: ignore [missing-import]

# --- Canonical CallInput DTO ---
class CallInput(BaseModel):
    call_id: Optional[int] = None
    organization_id: Optional[int] = None
    team_id: Optional[int] = None
    advisor_id: Optional[int] = None
    source_id: Optional[int] = None
    audio_path: str
    original_filename: str
    mime_type: str
    duration: float = 0.0
    recorded_at: datetime
    language: Optional[str] = "en"
    metadata: Optional[Dict[str, Any]] = None

# --- Base Ingestion Connector ---
class BaseConnector:
    """
    Abstract Base Ingestion Connector.
    Converts diverse external inputs into the canonical CallInput DTO.
    """
    def ingest(self, source_data: Any) -> CallInput:
        raise NotImplementedError("Connectors must implement the 'ingest' method.")

# --- Functional Manual Upload Connector ---
class ManualUploadConnector(BaseConnector):
    def ingest(self, source_data: Dict[str, Any]) -> CallInput:
        """
        Ingests calls manually uploaded by the user via Streamlit.
        Expects keys:
        - audio_path
        - original_filename
        - mime_type
        - duration
        - organization_id
        - team_id
        - advisor_id
        - source_id
        """
        return CallInput(
            organization_id=source_data.get("organization_id"),
            team_id=source_data.get("team_id"),
            advisor_id=source_data.get("advisor_id"),
            source_id=source_data.get("source_id"),
            audio_path=source_data["audio_path"],
            original_filename=source_data["original_filename"],
            mime_type=source_data["mime_type"],
            duration=source_data.get("duration", 0.0),
            recorded_at=datetime.now(),
            language=source_data.get("language", "en"),
            metadata=source_data.get("metadata", {})
        )

# --- Extensible Future Stubs ---
class FileConnector(BaseConnector):
    """Stub connector for future file-system based sync integrations."""
    def ingest(self, source_data: Any) -> CallInput:
        raise NotImplementedError("FileConnector is a stub. Implement when integration details are finalized.")

class FolderConnector(BaseConnector):
    """Stub connector for future folder watcher daemon integrations."""
    def ingest(self, source_data: Any) -> CallInput:
        raise NotImplementedError("FolderConnector is a stub. Implement when integration details are finalized.")

class CRMConnector(BaseConnector):
    """Stub connector for CRM integrations (e.g. Salesforce, HubSpot)."""
    def ingest(self, source_data: Any) -> CallInput:
        raise NotImplementedError("CRMConnector is a stub. Implement when integration details are finalized.")

class TelephonyConnector(BaseConnector):
    """Stub connector for dialer platforms (e.g. Twilio, RingCentral)."""
    def ingest(self, source_data: Any) -> CallInput:
        raise NotImplementedError("TelephonyConnector is a stub. Implement when integration details are finalized.")

class APIConnector(BaseConnector):
    """Stub connector for webhook and external REST API integrations."""
    def ingest(self, source_data: Any) -> CallInput:
        raise NotImplementedError("APIConnector is a stub. Implement when integration details are finalized.")
