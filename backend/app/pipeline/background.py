from fastapi import BackgroundTasks  # type: ignore
from backend.app.database.session import SessionLocal
from backend.app.models.call import Call as CallModel, CallStatus
from backend.app.pipeline.call_processor import CallProcessor
from backend.app.utils.timeline import log_pipeline_event
from backend.app.core.logging import get_logger

logger = get_logger("PIPELINE")

def trigger_call_processing(call_id: int, background_tasks: BackgroundTasks) -> None:
    """
    Transitions the Call status to 'Queued', logs the pipeline event,
    and schedules CallProcessor.process as a non-blocking FastAPI BackgroundTask.
    """
    db = SessionLocal()
    try:
        call = db.query(CallModel).filter(CallModel.id == call_id).first()
        if call:
            call.status = CallStatus.Queued
            call.progress = 5
            db.commit()
            db.refresh(call)
            
            # Record timeline trace
            log_pipeline_event(call_id, "Queued")
            logger.info("Call queued")
            
            # Enqueue call processor execution
            processor = CallProcessor()
            background_tasks.add_task(processor.process, call_id)
        else:
            logger.error(f"Could not find Call ID {call_id} to queue for pipeline processing.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error transitioning Call ID {call_id} status to Queued: {e}")
    finally:
        db.close()
