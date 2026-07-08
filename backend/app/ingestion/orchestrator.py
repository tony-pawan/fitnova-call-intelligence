import os
import shutil
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from fastapi import BackgroundTasks  # pyrefly: ignore [missing-import]

from backend.app.models.call import Call, CallStatus
from backend.app.ingestion.factory import ConnectorFactory
from backend.app.ingestion.dto import AudioInput
from backend.app.utils.metadata import extract_audio_metadata
from backend.app.core.logging import get_logger
from backend.app.pipeline.background import trigger_call_processing

logger = get_logger("INGESTION")

class IngestionOrchestrator:
    """
    Orchestration service coordinating calls ingestion across all connectors,
    persisting call metadata records in the DB, localizing recording audio files,
    and triggering downstream AI pipeline execution.
    """
    @staticmethod
    def ingest(
        db: Session,
        source_type: str,
        background_tasks: BackgroundTasks = None,
        **kwargs
    ) -> List[Call]:
        logger.info(f"Ingesting recordings via source: {source_type}")
        
        # 1. Instantiate connector from factory
        # Pass db context to connectors that require it (e.g. Folder)
        connector_kwargs = {"db": db} if source_type.lower() == "folder" else {}
        connector_kwargs.update(kwargs)
        
        connector = ConnectorFactory.get_connector(source_type, **connector_kwargs)
        
        # 2. Fetch and normalize DTOs
        audio_inputs: List[AudioInput] = connector.fetch()
        
        ingested_calls: List[Call] = []
        for audio_input in audio_inputs:
            try:
                # 3. Create database Call record
                db_call = Call(
                    original_filename=audio_input.original_filename,
                    stored_filename="",  # will update after assigning call ID
                    audio_path="",       # will update
                    mime_type=audio_input.mime_type,
                    file_size_bytes=os.path.getsize(audio_input.audio_path),
                    duration_seconds=0.0,
                    status=CallStatus.Uploaded,
                    language="hi" if "hindi-mix" in audio_input.original_filename.lower() else "en",
                    progress=0,
                    source=audio_input.source,
                    vendor=audio_input.vendor,
                    external_call_id=audio_input.external_call_id,
                    customer_name=audio_input.customer_name,
                    advisor_name=audio_input.advisor_name,
                    ingestion_metadata=json.dumps(audio_input.metadata),
                    organization_id=getattr(audio_input, "organization_id", None),
                    team_id=getattr(audio_input, "team_id", None),
                    advisor_id=getattr(audio_input, "advisor_id", None),
                    source_id=getattr(audio_input, "source_id", None)
                )
                db.add(db_call)
                db.flush()  # assign database ID to db_call
                
                # 4. Localize audio file in permanent storage directory
                ext = os.path.splitext(audio_input.original_filename)[1].lower()
                stored_filename = f"call_{db_call.id}{ext}"
                target_path = os.path.abspath(f"./storage/audio/{stored_filename}")
                
                os.makedirs("./storage/audio", exist_ok=True)
                
                # Copy from temp/watch path to permanent storage
                shutil.copy2(audio_input.audio_path, target_path)
                
                # Extract duration using mutagen
                metadata = extract_audio_metadata(target_path)
                
                # Update call path & stored filename details
                db_call.stored_filename = stored_filename
                db_call.audio_path = target_path
                db_call.duration_seconds = metadata.get("duration_seconds", 0.0)
                
                db.commit()
                db.refresh(db_call)
                
                logger.info(f"Ingested recording ID {db_call.id} ('{db_call.original_filename}') successfully.")
                
                # 5. Trigger asynchronous processing pipeline
                if background_tasks:
                    trigger_call_processing(db_call.id, background_tasks)
                else:
                    # Thread fallback for manual/CLI imports outside fastapi request scope
                    import threading
                    from backend.app.pipeline.call_processor import CallProcessor
                    
                    def run_pipeline():
                        try:
                            processor = CallProcessor()
                            processor.process(db_call.id)
                        except Exception as pe:
                            logger.error(f"Async pipeline thread failed for Call ID {db_call.id}: {pe}")
                            
                    threading.Thread(target=run_pipeline, daemon=True).start()
                    
                ingested_calls.append(db_call)
                
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to ingest call recording {audio_input.original_filename}: {e}")
                # Try to clean up copied file if failed
                if 'target_path' in locals() and os.path.exists(target_path):
                    try:
                        os.remove(target_path)
                    except:
                        pass
                raise
                
        return ingested_calls
