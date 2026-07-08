from abc import ABC, abstractmethod
from typing import List
from backend.app.ingestion.dto import AudioInput

class SourceConnector(ABC):
    """
    Abstract Base Class defining the standard interface for all sales call recording ingestion connectors.
    """
    @abstractmethod
    def connect(self) -> bool:
        """
        Verifies connectivity, authenticates API credentials, or validates directory target configurations.
        """
        pass

    @abstractmethod
    def validate(self, *args, **kwargs) -> bool:
        """
        Performs pre-ingestion validation (e.g. verify audio files exist, check required CSV metadata schema).
        """
        pass

    @abstractmethod
    def fetch(self, *args, **kwargs) -> List[AudioInput]:
        """
        Retrieves, downloads, or watches for incoming recordings and maps them into a list of normalized DTOs.
        """
        pass

    @abstractmethod
    def normalize(self, raw_data: any) -> AudioInput:
        """
        Converts custom vendor or raw directory source details into a unified AudioInput DTO.
        """
        pass
