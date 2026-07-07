import os
import json
from datetime import datetime
from backend.app.core.logging import get_logger

logger = get_logger("PIPELINE")

def log_pipeline_event(call_id: int, event_name: str) -> None:
    """
    Emits a structured log prefix [PIPELINE] and writes the timeline event
    asynchronous state transitions to a local JSON file: storage/processed/call_{call_id}_timeline.json.
    """
    # 1. Log structured trace
    logger.info(f"Call {call_id}: {event_name}")
    
    # 2. Write to lightweight file-system timeline JSON
    timeline_dir = "./storage/processed"
    os.makedirs(timeline_dir, exist_ok=True)
    timeline_path = os.path.join(timeline_dir, f"call_{call_id}_timeline.json")
    
    events = []
    if os.path.exists(timeline_path):
        try:
            with open(timeline_path, "r") as f:
                events = json.load(f)
        except Exception:
            events = []
            
    events.append({
        "timestamp": datetime.now().isoformat(),
        "event": event_name
    })
    
    try:
        with open(timeline_path, "w") as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write timeline event to filesystem: {e}")

def get_pipeline_timeline(call_id: int) -> list:
    """
    Retrieves the pipeline timeline events list for a given Call ID.
    Returns an empty list if no events have occurred.
    """
    timeline_path = os.path.join("./storage/processed", f"call_{call_id}_timeline.json")
    if os.path.exists(timeline_path):
        try:
            with open(timeline_path, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []
