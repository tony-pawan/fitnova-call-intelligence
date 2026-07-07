from abc import ABC, abstractmethod
from backend.app.ai.dto.transcript import TranscriptResult

class Transcriber(ABC):
    """
    Abstract interface for audio transcription engine services.
    Ensures structural modularity across different transcriber engines.
    """
    @abstractmethod
    def transcribe(self, audio_path: str) -> TranscriptResult:
        """
        Transcribes the target audio recording at audio_path.
        Returns a TranscriptResult DTO containing segment and duration metadata.
        """
        pass
