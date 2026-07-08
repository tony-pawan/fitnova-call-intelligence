from typing import List, Optional
from pydantic import BaseModel  # pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException, BackgroundTasks  # pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.database.session import get_db
from backend.app.services.upload_service import UploadService
from backend.app.services.call_service import CallService
from backend.app.schemas.call import Call
from backend.app.models.call import Call as CallModel
from backend.app.utils.timeline import get_pipeline_timeline

router = APIRouter(prefix="/calls", tags=["Calls"])

# Instantiate the instance-based upload service
upload_service = UploadService()

@router.post("/upload")
def upload_call(
    audio_file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Ingests call audio files, registers database configurations, and triggers background processing.
    """
    # Enforce background tasks instance availability
    if background_tasks is None:
        background_tasks = BackgroundTasks()
        
    db_call = upload_service.upload_call(
        db=db, 
        audio_file=audio_file,
        background_tasks=background_tasks
    )
    
    return {
        "success": True,
        "call_id": db_call.id,
        "status": db_call.status.value,
        "original_filename": db_call.original_filename,
        "duration_seconds": db_call.duration_seconds
    }

import os
import json

@router.get("", response_model=List[Call])
def get_calls(db: Session = Depends(get_db)):
    """
    Retrieves all calls, ordered by creation date descending (newest uploads first).
    """
    return db.query(CallModel).order_by(CallModel.created_at.desc()).all()

@router.get("/{call_id}", response_model=Call)
def get_call(call_id: int, db: Session = Depends(get_db)):
    """
    Retrieves metadata and timeline events for a specific call recording by ID.
    """
    db_call = CallService.get_call(db, call_id=call_id)
    if not db_call:
        raise HTTPException(
            status_code=404, 
            detail=f"Call record with ID {call_id} not found."
        )
    
    # Resolve timeline from disk storage
    db_call.timeline = get_pipeline_timeline(call_id)
    return db_call

# Pydantic schemas for feedback loop request payloads
class TranscriptCorrectionSchema(BaseModel):
    index: int
    text: str

class TranscriptCorrectionRequest(BaseModel):
    corrections: List[TranscriptCorrectionSchema]

class SpeakerCorrectionSchema(BaseModel):
    index: int
    speaker: str

class SpeakerCorrectionRequest(BaseModel):
    speaker_updates: List[SpeakerCorrectionSchema]

class IssueReviewRequest(BaseModel):
    review_status: str
    reviewer_comments: Optional[str] = None
    severity: Optional[str] = None

class ScoreOverrideRequest(BaseModel):
    human_score: float
    reason: str
    reviewer: str

from backend.app.ingestion.orchestrator import IngestionOrchestrator
from backend.app.services.feedback_service import FeedbackService
from backend.app.services.dashboard_service import DashboardService

# API Routes
@router.post("/ingest")
def ingest_call(
    source_type: str = Form(...),
    folder_path: Optional[str] = Form(None),
    crm_metadata_file: Optional[UploadFile] = File(None),
    crm_audio_dir: Optional[str] = Form(None),
    vendor: Optional[str] = Form(None),
    external_call_id: Optional[str] = Form(None),
    api_audio_file: Optional[UploadFile] = File(None),
    api_metadata_json: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """
    Unified entrypoint for all ingestion connector sources (Manual Upload,
    Local folder scan, CRM spreadsheet parsing, REST API submission,
    and Telephony/Dialer vendor simulator events).
    """
    if background_tasks is None:
        background_tasks = BackgroundTasks()

    try:
        ingest_kwargs = {}
        src = source_type.lower()
        
        if src == "upload":
            if not api_audio_file:
                raise HTTPException(status_code=400, detail="Missing Upload audio file")
            os.makedirs("./storage/temp_uploads", exist_ok=True)
            temp_path = os.path.abspath(f"./storage/temp_uploads/{api_audio_file.filename}")
            with open(temp_path, "wb") as f:
                f.write(api_audio_file.file.read())
            
            ingest_kwargs = {
                "filename": api_audio_file.filename,
                "temp_path": temp_path,
                "size_bytes": os.path.getsize(temp_path),
                "metadata": {"vendor": "Direct Manual Upload"}
            }
            
        elif src == "folder":
            if not folder_path:
                raise HTTPException(status_code=400, detail="Folder watch path is required for folder Ingestion")
            ingest_kwargs = {
                "folder_path": folder_path
            }
            
        elif src == "crm":
            if not crm_metadata_file or not crm_audio_dir:
                raise HTTPException(status_code=400, detail="CRM metadata sheet (CSV) and audio directory path are required")
            os.makedirs("./storage/temp_crm", exist_ok=True)
            temp_csv_path = os.path.abspath(f"./storage/temp_crm/{crm_metadata_file.filename}")
            with open(temp_csv_path, "wb") as f:
                f.write(crm_metadata_file.file.read())
            ingest_kwargs = {
                "metadata_file_path": temp_csv_path,
                "audio_directory_path": crm_audio_dir
            }
            
        elif src == "api":
            if not api_audio_file or not external_call_id:
                raise HTTPException(status_code=400, detail="API audio file and external call ID are required")
            os.makedirs("./storage/temp_api", exist_ok=True)
            temp_path = os.path.abspath(f"./storage/temp_api/{api_audio_file.filename}")
            with open(temp_path, "wb") as f:
                f.write(api_audio_file.file.read())
            
            meta = {}
            if api_metadata_json:
                try:
                    meta = json.loads(api_metadata_json)
                except Exception as je:
                    raise HTTPException(status_code=400, detail=f"Invalid JSON metadata parameter: {je}")
                    
            ingest_kwargs = {
                "filename": api_audio_file.filename,
                "temp_path": temp_path,
                "external_call_id": external_call_id,
                "metadata": meta
            }
            
        elif src in ["telephony", "dialer"]:
            ingest_kwargs = {
                "vendor": vendor or ("Twilio" if src == "telephony" else "Five9"),
                "config": {"credentials": {"api_key": "simulated_api_key"}}
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported Ingestion source type: {source_type}")
            
        calls = IngestionOrchestrator.ingest(
            db=db,
            source_type=source_type,
            background_tasks=background_tasks,
            **ingest_kwargs
        )
        
        if src in ["upload", "crm", "api"] and 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
                
        return {
            "success": True,
            "count": len(calls),
            "ingested_calls": [
                {
                    "id": c.id,
                    "filename": c.original_filename,
                    "status": c.status.value,
                    "source": c.source,
                    "vendor": c.vendor
                } for c in calls
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

@router.get("/dashboard/metrics")
def get_dashboard_operational_metrics(db: Session = Depends(get_db)):
    """
    Exposes enriched operational statistics and ingestion health trends.
    """
    return DashboardService.get_dashboard_metrics(db)

@router.post("/{call_id}/feedback/transcript")
def correct_call_transcript(
    call_id: int,
    request: TranscriptCorrectionRequest,
    db: Session = Depends(get_db)
):
    """
    Updates transcript text content for specific segments, saving version backups.
    """
    try:
        corrections_list = [{"index": c.index, "text": c.text} for c in request.corrections]
        success = FeedbackService.correct_transcript(db, call_id, corrections_list)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{call_id}/feedback/speakers")
def correct_call_speakers(
    call_id: int,
    request: SpeakerCorrectionRequest,
    db: Session = Depends(get_db)
):
    """
    Updates speaker labels mapping conversation segments.
    """
    try:
        updates_list = [{"index": u.index, "speaker": u.speaker} for u in request.speaker_updates]
        success = FeedbackService.correct_speakers(db, call_id, updates_list)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/issues/{issue_id}/review")
def review_issue_tag(
    issue_id: int,
    request: IssueReviewRequest,
    db: Session = Depends(get_db)
):
    """
    Reviews a specific compliance issue, marking it as accepted, dismissed, or a false positive.
    """
    try:
        success = FeedbackService.review_issue(
            db=db,
            issue_id=issue_id,
            review_status=request.review_status,
            reviewer_comments=request.reviewer_comments,
            severity=request.severity
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{call_id}/feedback/score")
def override_analysis_score(
    call_id: int,
    request: ScoreOverrideRequest,
    db: Session = Depends(get_db)
):
    """
    Overrides the AI audit scorecard overall score with human evaluator assessment.
    """
    try:
        success = FeedbackService.override_score(
            db=db,
            call_id=call_id,
            human_score=request.human_score,
            reason=request.reason,
            reviewer=request.reviewer
        )
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{call_id}/reanalyze")
def trigger_call_reanalysis(
    call_id: int,
    db: Session = Depends(get_db)
):
    """
    Re-runs the LLM prompt templates and score evaluations on corrected transcripts.
    """
    try:
        success = FeedbackService.reanalyze(db, call_id)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{call_id}/versions")
def get_call_version_history(
    call_id: int,
    db: Session = Depends(get_db)
):
    """
    Lists the complete file version histories for transcripts, conversations, and analyses.
    """
    try:
        history = FeedbackService.get_version_history(db, call_id)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
