from typing import List
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
