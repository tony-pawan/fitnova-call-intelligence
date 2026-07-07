from abc import ABC, abstractmethod
from backend.app.ai.dto.conversation import ConversationResult

class Diarizer(ABC):
    """
    Abstract interface for speaker diarization service engine.
    Modularity ensures different diarization backends can be swapped in.
    """
    @abstractmethod
    def diarize(self, transcript_json_path: str, audio_path: str) -> ConversationResult:
        """
        Combines transcription intervals from the transcript JSON file with
        speaker turns diarized from the audio file to reconstruct the conversation.
        
        Returns a ConversationResult DTO.
        """
        pass
