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
        api_key = settings.GEMINI_API_KEY
        
        if api_key and api_key != "mock_key_for_development":
            try:
                logger.info("Performing transcription via Gemini API for Hinglish accuracy")
                import google.generativeai as genai
                from pydantic import BaseModel
                from typing import List
                import json
                
                genai.configure(api_key=api_key)
                
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()
                    
                ext = os.path.splitext(audio_path)[1].lower()
                mime_type = "audio/mp3"
                if ext == ".wav":
                    mime_type = "audio/wav"
                elif ext == ".m4a":
                    mime_type = "audio/m4a"
                elif ext == ".aac":
                    mime_type = "audio/aac"
                    
                class SegmentSchema(BaseModel):
                    start: float
                    end: float
                    text: str
                    
                class TranscriptSchema(BaseModel):
                    language: str
                    duration: float
                    segments: List[SegmentSchema]
                    
                prompt = (
                    "You are an expert verbatim speech-to-text transcriber specializing in Hinglish (mixed Hindi and English). "
                    "Listen to the audio recording. Transcribe the audio verbatim in Hinglish. "
                    "For Hindi speech, transcribe it using the Roman/Latin script (e.g. 'haan', 'bolie', 'gym ja rahe' instead of Devanagari script) "
                    "so that the transcript is Romanized. Do NOT translate the Hindi speech into English. "
                    "For English speech, transcribe it in English. "
                    "Output the result in structured JSON format matching the schema."
                )
                
                max_retries = 3
                backoff = 12.0
                response_text = None
                model_name = "gemini-2.5-flash-lite"
                
                for attempt in range(max_retries + 1):
                    try:
                        logger.info(f"Gemini transcription request started (attempt {attempt + 1})")
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(
                            [
                                {
                                    "mime_type": mime_type,
                                    "data": audio_bytes
                                },
                                prompt
                            ],
                            generation_config=genai.GenerationConfig(
                                response_mime_type="application/json",
                                response_schema=TranscriptSchema,
                                temperature=0.1
                            )
                        )
                        response_text = response.text
                        break
                    except Exception as ex:
                        err_msg = str(ex)
                        is_rate_limit = "429" in err_msg or "quota" in err_msg or "ResourceExhausted" in err_msg or "rate limit" in err_msg
                        is_daily_limit = "PerDay" in err_msg or "daily" in err_msg
                        
                        if is_rate_limit and not is_daily_limit and attempt < max_retries:
                            logger.warning(f"Gemini API rate limit exceeded during transcription. Retrying in {backoff} seconds...")
                            time.sleep(backoff)
                            backoff *= 2
                            continue
                        raise ex
                
                if not response_text:
                    raise RuntimeError("Empty response received from Gemini transcription")
                    
                data = json.loads(response_text)
                
                segments = []
                for s in data.get("segments", []):
                    segments.append(
                        TranscriptSegment(
                            start=round(s.get("start", 0.0), 2),
                            end=round(s.get("end", 0.0), 2),
                            text=s.get("text", "").strip(),
                            confidence=1.0
                        )
                    )
                    
                execution_time = time.time() - start_time
                logger.info(f"Gemini transcription successful! Generated {len(segments)} segments in {execution_time:.2f} seconds.")
                return TranscriptResult(
                    language=data.get("language", "hi"),
                    duration=round(data.get("duration", 0.0), 2),
                    segments=segments
                )
            except Exception as e:
                logger.error(f"Gemini transcription failed: {e}. Falling back to local Faster Whisper.")
                
        # --- Local Faster Whisper Fallback ---
        logger.info("Executing local Faster Whisper transcription")
        model = self.get_model()
        try:
            segments_generator, info = model.transcribe(
                audio_path,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_speech_duration_ms=250),
                initial_prompt="Main Arjun bol raha hoon FitNova se. This is a sales call with a mix of Hindi and English (Hinglish). Haan sir, structure send kar dijiye. Okay sure."
            )
            
            logger.info(f"Language detected: {info.language}")
            
            segments = []
            for segment in segments_generator:
                confidence = None
                if hasattr(segment, "avg_logprob"):
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
