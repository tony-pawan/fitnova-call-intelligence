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
                try:
                    cls._pipeline_instance = PyannotePipeline.from_pretrained(
                        model_name,
                        token=auth_token
                    )
                except TypeError:
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

        # 2. Execute Pyannote diarization pipeline or use mock fallback
        gemini_api_key = settings.GEMINI_API_KEY
        
        if gemini_api_key and gemini_api_key != "mock_key_for_development":
            try:
                logger.info("Performing speaker diarization via Gemini API")
                import google.generativeai as genai
                from pydantic import BaseModel
                from typing import List
                import json
                
                genai.configure(api_key=gemini_api_key)
                
                with open(audio_path, "rb") as f:
                    audio_bytes = f.read()
                    
                text_segments = []
                for idx, s in enumerate(transcript_data["segments"]):
                    text_segments.append({
                        "index": idx,
                        "start": s["start"],
                        "end": s["end"],
                        "text": s["text"]
                    })
                    
                class DiarizationSegmentSchema(BaseModel):
                    index: int
                    speaker: str  # must be "Advisor" or "Customer"
                    
                class DiarizationSchema(BaseModel):
                    segments: List[DiarizationSegmentSchema]
                    
                prompt = (
                    "You are an expert sales call diarizer. You are given an audio file and its transcribed text segments with indices.\n"
                    "Your task is to assign the correct speaker label ('Advisor' or 'Customer') to each segment index.\n"
                    "The 'Advisor' represents the FitNova company (pitching, explaining programs, introducing, asking discovery questions).\n"
                    "The 'Customer' is the person interested in fitness (answering questions, asking about cost, mentioning goals like muscle gain, having objections).\n"
                    "Listen to the audio context to match speakers accurately to the text.\n"
                    "Here are the text segments:\n"
                    f"{json.dumps(text_segments, indent=2)}\n\n"
                    "Output the result in structured JSON format matching the schema."
                )
                
                ext = os.path.splitext(audio_path)[1].lower()
                mime_type = "audio/mp3"
                if ext == ".wav":
                    mime_type = "audio/wav"
                elif ext == ".m4a":
                    mime_type = "audio/m4a"
                elif ext == ".aac":
                    mime_type = "audio/aac"
                    
                model_name = settings.GEMINI_MODEL
                logger.info("Gemini diarization request started")
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
                        response_schema=DiarizationSchema,
                        temperature=0.1
                    ),
                    request_options={"timeout": 15.0}
                )
                response_text = response.text
                        
                if not response_text:
                    raise RuntimeError("Empty response received from Gemini diarization")
                    
                diarization_data = json.loads(response_text)
                speaker_map = {item["index"]: item["speaker"] for item in diarization_data.get("segments", [])}
                
                conversation_segments = []
                for idx, segment in enumerate(transcript_data["segments"]):
                    mapped_spk = speaker_map.get(idx, "Speaker 1")
                    if mapped_spk not in ["Advisor", "Customer"]:
                        mapped_spk = "Advisor" if idx % 2 == 0 else "Customer"
                        
                    conversation_segments.append(
                        ConversationSegment(
                            speaker=mapped_spk,
                            start=segment["start"],
                            end=segment["end"],
                            text=segment["text"]
                        )
                    )
                    
                execution_time = time.time() - start_time
                logger.info(f"Gemini speaker diarization successful in {execution_time:.2f} seconds.")
                return ConversationResult(
                    language=transcript_data.get("language", "hi"),
                    duration=transcript_data.get("duration", 0.0),
                    segments=conversation_segments
                )
            except Exception as e:
                logger.error(f"Gemini speaker diarization failed: {e}. Falling back to Pyannote diarization.")
                
        auth_token = settings.PYANNOTE_AUTH_TOKEN
        is_mock = (not auth_token or "mock" in auth_token.lower() or "your_huggingface" in auth_token.lower())
        
        pipeline = None
        if not is_mock:
            try:
                pipeline = self.get_pipeline()
            except Exception as init_err:
                logger.warning(f"Failed to initialize live Pyannote pipeline: {init_err}. Falling back to mock diarization mode.")
                is_mock = True

        diarization_turns: List[Dict[str, Any]] = []
        if is_mock or pipeline is None:
            logger.info("Executing pyannote diarization in mock/fallback mode")
            for idx, segment in enumerate(transcript_data["segments"]):
                speaker_id = "SPEAKER_00" if idx % 2 == 0 else "SPEAKER_01"
                diarization_turns.append({
                    "start": segment["start"],
                    "end": segment["end"],
                    "speaker": speaker_id
                })
        else:
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
                logger.warning(f"Error during pyannote audio execution: {e}. Falling back to mock diarization mode.")
                diarization_turns = []
                for idx, segment in enumerate(transcript_data["segments"]):
                    speaker_id = "SPEAKER_00" if idx % 2 == 0 else "SPEAKER_01"
                    diarization_turns.append({
                        "start": segment["start"],
                        "end": segment["end"],
                        "speaker": speaker_id
                    })
            
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
