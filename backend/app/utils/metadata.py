import mutagen  # pyrefly: ignore [missing-import]
from backend.app.core.logging import get_logger

logger = get_logger("UPLOAD")

def extract_audio_metadata(file_path: str) -> dict:
    """
    Extracts the duration of the audio file in seconds using the mutagen library.
    """
    logger.info("[UPLOAD] Metadata extracted")
    try:
        audio = mutagen.File(file_path)
        if audio is not None and audio.info is not None:
            duration = getattr(audio.info, "length", 0.0)
            return {
                "duration_seconds": float(duration)
            }
        else:
            logger.warning(f"[UPLOAD] Mutagen was unable to parse audio info for: {file_path}")
    except Exception as e:
        logger.error(f"[UPLOAD] Error extracting audio metadata: {e}")
        
    return {
        "duration_seconds": 0.0
    }
