import traceback
from sqlalchemy.orm import Session  # pyrefly: ignore [missing-import]
from backend.app.database.session import SessionLocal
from backend.app.models.call import Call as CallModel, CallStatus
from backend.app.utils.timeline import log_pipeline_event
from backend.app.ai.transcriber import Transcriber
from backend.app.ai.faster_whisper import FasterWhisperTranscriber
from backend.app.ai.diarizer import Diarizer
from backend.app.ai.pyannote_diarizer import PyannoteDiarizer
from backend.app.ai.analysis_orchestrator import AnalysisOrchestrator
from backend.app.ai.dto.conversation import ConversationResult
from backend.app.utils.json_storage import load_json
from backend.app.services.transcript_storage_service import TranscriptStorageService
from backend.app.services.conversation_storage_service import ConversationStorageService
from backend.app.services.analysis_storage_service import AnalysisStorageService
from backend.app.core.logging import get_logger

logger = get_logger("PIPELINE")

class CallProcessor:
    """
    Orchestration class that coordinates the sequential phases of the
    FitNova Sales Call Intelligence System.
    
    Phases:
      Queued ➔ Processing ➔ Transcription ➔ Diarization ➔ PII Redaction ➔ AI Analysis ➔ Completed
    """
    def __init__(
        self, 
        transcriber: Transcriber = None, 
        diarizer: Diarizer = None,
        orchestrator: AnalysisOrchestrator = None
    ) -> None:
        # Decouple CallProcessor from concrete engines via dependency injection
        self.transcriber = transcriber or FasterWhisperTranscriber()
        self.diarizer = diarizer or PyannoteDiarizer()
        self.orchestrator = orchestrator or AnalysisOrchestrator()

    def process(self, call_id: int) -> None:
        """
        Public method to execute the complete pipeline sequence asynchronously.
        Catches any failures, marks call status to Failed, and logs stack traces.
        """
        db: Session = SessionLocal()
        try:
            # 1. Fetch Call from Database
            call = db.query(CallModel).filter(CallModel.id == call_id).first()
            if not call:
                logger.error(f"Call record ID {call_id} not found in database during background process check.")
                return

            # 2. Transition Status: Processing
            self._change_status(db, call, CallStatus.Processing)
            log_pipeline_event(call_id, "Processing Started")

            # 3. Sequential Stage Executions
            self._transcribe(db, call)
            self._diarize(db, call)
            self._redact_pii(db, call)
            self._analyze(db, call)

            # 4. Final Transition: Completed
            self._complete(db, call)
            
        except Exception as e:
            db.rollback()
            err_trace = traceback.format_exc()
            logger.error(f"Error encountered during pipeline execution for Call ID {call_id}:\n{err_trace}")
            
            try:
                # Re-fetch call entity to update failed state status
                call = db.query(CallModel).filter(CallModel.id == call_id).first()
                if call:
                    self._fail(db, call, e)
            except Exception as fail_err:
                logger.error(f"Failed to set database status to Failed for Call ID {call_id}: {fail_err}")
                
        finally:
            db.close()

    def _change_status(self, db: Session, call: CallModel, status: CallStatus) -> None:
        """
        Helper method to transition call statuses on the database transaction layer.
        """
        call.status = status
        db.commit()
        db.refresh(call)

    def _transcribe(self, db: Session, call: CallModel) -> None:
        """
        Executes Speech-to-Text Transcription using the injected Transcriber service.
        Persists segments to PostgreSQL and saves the complete JSON transcription metadata.
        """
        log_pipeline_event(call.id, "Transcription Started")
        
        # Perform transcription
        result = self.transcriber.transcribe(call.audio_path)
        
        # Save detected language to Call metadata
        call.language = result.language
        db.commit()
        db.refresh(call)
        
        log_pipeline_event(call.id, "Language Detected")
        log_pipeline_event(call.id, "Transcript Generated")

        # Delegate storage operations to the TranscriptStorageService
        TranscriptStorageService.persist_transcript(db, call.id, result)
        log_pipeline_event(call.id, "Transcript Stored")

    def _diarize(self, db: Session, call: CallModel) -> None:
        """
        Executes speaker diarization and conversation reconstruction using the Diarizer service.
        """
        log_pipeline_event(call.id, "Speaker Diarization Started")
        
        transcript_json_path = f"./storage/transcripts/call_{call.id}.json"
        
        # Perform speaker diarization and alignment
        result = self.diarizer.diarize(transcript_json_path, call.audio_path)
        
        # Record timeline events
        unique_speakers = len(set(s.speaker for s in result.segments))
        log_pipeline_event(call.id, f"Detected {unique_speakers} speakers")
        log_pipeline_event(call.id, "Conversation Reconstructed")
        
        # Delegate conversation persistence to the storage service
        ConversationStorageService.persist_conversation(db, call.id, result)
        log_pipeline_event(call.id, "Conversation Stored")

    def _redact_pii(self, db: Session, call: CallModel) -> None:
        """
        Placeholder method for PII masking/redaction.
        """
        log_pipeline_event(call.id, "PII Redaction Started")
        logger.info("PII placeholder executed")

    def _analyze(self, db: Session, call: CallModel) -> None:
        """
        Executes Google Gemini multi-agent conversational scorecards audits.
        Persists results to call_analyses table and writes analysis.json files to local storage.
        """
        log_pipeline_event(call.id, "AI Analysis Started")
        
        # Load conversation JSON file and map it to ConversationResult DTO
        conversation_json_path = f"./storage/conversations/call_{call.id}.json"
        conv_data = load_json(conversation_json_path)
        if not conv_data:
            raise FileNotFoundError(f"Conversation JSON file not found at: {conversation_json_path}")
            
        conversation_dto = ConversationResult.model_validate(conv_data)
        
        # Trigger the analysis orchestrator
        result = self.orchestrator.analyze(call.id, conversation_dto)
        
        # Persist scorecards output
        AnalysisStorageService.persist_analysis(db, call.id, result)
        log_pipeline_event(call.id, "Analysis Stored")

    def _complete(self, db: Session, call: CallModel) -> None:
        """
        Finalizes call processing, transitioning status to Completed.
        """
        self._change_status(db, call, CallStatus.Completed)
        log_pipeline_event(call.id, "Completed")
        logger.info("Pipeline completed successfully")

    def _fail(self, db: Session, call: CallModel, error: Exception) -> None:
        """
        Marks call processing as Failed on error.
        """
        self._change_status(db, call, CallStatus.Failed)
        log_pipeline_event(call.id, "Failed")
        logger.info(f"Pipeline marked as Failed: {error}")
