import os
import time
from faster_whisper import WhisperModel  # pyrefly: ignore [missing-import]
from backend.app.ai.transcriber import Transcriber
from backend.app.ai.dto.transcript import TranscriptResult, TranscriptSegment
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger("TRANSCRIPTION")

class FasterWhisperTranscriber(Transcriber):
    # Class-level model singleton to prevent duplicate reloads
    _model_instance = None

    @classmethod
    def get_model(cls) -> WhisperModel:
        """
        Retrieves the singleton WhisperModel instance, initializing it exactly once.
        """
        if cls._model_instance is None:
            logger.info("Loading Faster Whisper model")
            model_size = settings.WHISPER_MODEL
            device = settings.WHISPER_DEVICE
            compute_type = settings.WHISPER_COMPUTE_TYPE
            
            logger.info(f"Initializing WhisperModel '{model_size}' on '{device}' with '{compute_type}'")
            try:
                cls._model_instance = WhisperModel(
                    model_size,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=4
                )
                logger.info("Faster Whisper model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load Faster Whisper model: {e}")
                raise
        return cls._model_instance

    def transcribe(self, audio_path: str) -> TranscriptResult:
        """
        Transcribes the given audio file using Faster Whisper.
        Returns a TranscriptResult DTO.
        """
        logger.info("Starting transcription")
        
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            raise FileNotFoundError(f"Audio file not found at path: {audio_path}")

        start_time = time.time()
        model = self.get_model()

        # Execute transcription with Voice Activity Detection (VAD) and beam search quality settings
        # CT2 returns a generator of segments, which we parse dynamically
        try:
            segments_generator, info = model.transcribe(
                audio_path,
                beam_size=2,
                vad_filter=True,
                vad_parameters=dict(min_speech_duration_ms=250)
            )
            
            logger.info(f"Language detected: {info.language}")
            
            segments = []
            for segment in segments_generator:
                # Calculate confidence score if available. 
                # Whisper segment carries 'avg_logprob' or 'no_speech_prob'
                # avg_logprob is typical log probability. We translate this or pass it.
                confidence = None
                if hasattr(segment, "avg_logprob"):
                    # Quick math: convert log probability to confidence percentage (0 to 1)
                    import math
                    confidence = round(math.exp(max(segment.avg_logprob, -5.0)), 2)
                    
                segments.append(
                    TranscriptSegment(
                        start=round(segment.start, 2),
                        end=round(segment.end, 2),
                        text=segment.text.strip(),
                        confidence=confidence
                    )
                )
                
            execution_time = time.time() - start_time
            logger.info(f"Generated {len(segments)} transcript segments in {execution_time:.2f} seconds")
            
            return TranscriptResult(
                language=info.language,
                duration=round(info.duration, 2),
                segments=segments
            )
            
        except Exception as e:
            logger.error(f"Error during Faster Whisper execution: {e}")
            raise RuntimeError(f"Transcription failed: {e}")
