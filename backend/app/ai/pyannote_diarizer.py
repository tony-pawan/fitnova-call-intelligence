import os
import time
from typing import List, Dict, Any
from backend.app.ai.diarizer import Diarizer
from backend.app.ai.dto.conversation import ConversationResult, ConversationSegment
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.utils.json_storage import load_json

logger = get_logger("DIARIZATION")

class PyannoteDiarizer(Diarizer):
    # Class-level model pipeline instance to prevent duplicate loads
    _pipeline_instance = None

    @classmethod
    def get_pipeline(cls) -> Any:
        """
        Retrieves the singleton Pyannote speaker diarization pipeline instance,
        loading and mapping it to the target device exactly once.
        """
        if cls._pipeline_instance is None:
            logger.info("Loading pyannote model")
            model_name = settings.PYANNOTE_MODEL
            auth_token = settings.PYANNOTE_AUTH_TOKEN
            device_str = settings.PYANNOTE_DEVICE
            
            # Raise clear error if HF Token is missing or placeholder
            if not auth_token or "mock" in auth_token.lower() or "your_huggingface" in auth_token.lower():
                logger.error("Missing Hugging Face authentication token for pyannote.audio")
                raise ValueError("Hugging Face API token (PYANNOTE_AUTH_TOKEN) is not configured.")
                
            try:
                import torch
                from pyannote.audio import Pipeline as PyannotePipeline  # pyrefly: ignore [missing-import]
                
                logger.info(f"Initializing Pyannote Pipeline '{model_name}' on '{device_str}'")
                cls._pipeline_instance = PyannotePipeline.from_pretrained(
                    model_name,
                    use_auth_token=auth_token
                )
                
                if cls._pipeline_instance is None:
                    raise RuntimeError("Pyannote returned None from pretrained constructor")
                    
                if device_str:
                    cls._pipeline_instance.to(torch.device(device_str))
                    
                logger.info("Pyannote model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Pyannote speaker diarization model: {e}")
                raise RuntimeError(f"Pyannote initialization failed: {e}")
                
        return cls._pipeline_instance

    def diarize(self, transcript_json_path: str, audio_path: str) -> ConversationResult:
        """
        Runs pyannote diarization on the audio and aligns it with transcript segment timestamps.
        """
        start_time = time.time()
        
        # 1. Validate transcript JSON
        if not os.path.exists(transcript_json_path):
            raise FileNotFoundError(f"Transcript JSON file not found at: {transcript_json_path}")
            
        transcript_data = load_json(transcript_json_path)
        if not transcript_data or "segments" not in transcript_data:
            raise ValueError("Transcript JSON is empty or corrupted.")

        # 2. Execute Pyannote diarization pipeline
        pipeline = self.get_pipeline()
        
        diarization_turns: List[Dict[str, Any]] = []
        try:
            diarization = pipeline(audio_path)
            if diarization is not None:
                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    diarization_turns.append({
                        "start": turn.start,
                        "end": turn.end,
                        "speaker": speaker
                    })
        except Exception as e:
            logger.error(f"Error during pyannote audio execution: {e}")
            raise RuntimeError(f"Diarization processing failed: {e}")
            
        # Extract unique speaker labels
        unique_spks = sorted(list(set(t["speaker"] for t in diarization_turns)))
        logger.info(f"Detected {len(unique_spks)} speakers")

        # 3. Align transcript segments with speaker turns using maximum overlap
        for segment in transcript_data["segments"]:
            t_start = segment["start"]
            t_end = segment["end"]
            
            best_speaker = None
            max_overlap = 0.0
            
            for turn in diarization_turns:
                overlap = max(0.0, min(t_end, turn["end"]) - max(t_start, turn["start"]))
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = turn["speaker"]
                    
            segment["speaker_label"] = best_speaker if best_speaker is not None else "UNKNOWN"

        # 4. Map speaker labels using first-appearance rules:
        # First detected -> Advisor
        # Second detected -> Customer
        # If mapping is ambiguous (e.g. <= 1 speaker or empty), fallback to Speaker 1 / Speaker 2
        detected_speakers = []
        for segment in transcript_data["segments"]:
            lbl = segment["speaker_label"]
            if lbl != "UNKNOWN" and lbl not in detected_speakers:
                detected_speakers.append(lbl)
                
        speaker_mapping = {}
        if len(detected_speakers) >= 2:
            speaker_mapping[detected_speakers[0]] = "Advisor"
            speaker_mapping[detected_speakers[1]] = "Customer"
            for idx, other_lbl in enumerate(detected_speakers[2:], start=3):
                speaker_mapping[other_lbl] = f"Speaker {idx}"
        else:
            # Ambiguous speaker set - use fallback Speaker 1 / Speaker 2
            if len(detected_speakers) == 1:
                speaker_mapping[detected_speakers[0]] = "Speaker 1"
            speaker_mapping["UNKNOWN"] = "Speaker 1"
            
        # Reconstruct sequential ConversationSegment DTOs
        conversation_segments = []
        for segment in transcript_data["segments"]:
            raw_lbl = segment["speaker_label"]
            mapped_spk = speaker_mapping.get(raw_lbl, "Speaker 1")
            
            conversation_segments.append(
                ConversationSegment(
                    speaker=mapped_spk,
                    start=segment["start"],
                    end=segment["end"],
                    text=segment["text"]
                )
            )
            
        execution_time = time.time() - start_time
        logger.info("Conversation reconstruction complete")
        logger.info(f"Execution time: {execution_time:.2f} seconds")

        return ConversationResult(
            language=transcript_data.get("language", "en"),
            duration=transcript_data.get("duration", 0.0),
            segments=conversation_segments
        )
