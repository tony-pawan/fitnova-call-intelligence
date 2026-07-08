from typing import List, Dict, Any, Optional
from pydantic import BaseModel  # pyrefly: ignore [missing-import]

class CallResult(BaseModel):
    """
    Canonical processing output model for FitNova call intelligence pipeline.
    Combines SQL DB metrics, raw dialogue metadata, JSON artifacts, and human review updates.
    """
    call_id: int
    original_filename: str
    stored_filename: str
    audio_path: str
    duration_seconds: float
    status: str
    
    # Hierarchy mappings
    organization_id: Optional[int] = None
    team_id: Optional[int] = None
    advisor_id: Optional[int] = None
    source_id: Optional[int] = None
    source_name: str = "Manual Upload"
    
    # AI Scorecard Output
    overall_score: float
    summary: str
    recommendation: str
    
    # Dialogues and timeline artifacts
    transcript: Dict[str, Any]
    conversation: Dict[str, Any]
    analysis: Dict[str, Any]
    timeline: List[Dict[str, Any]]
    
    # Issue Tags & Human Feedback Statuses
    issue_tags: List[Dict[str, Any]]
    human_feedback_summary: Dict[str, Any]
