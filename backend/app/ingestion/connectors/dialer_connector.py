import os
import shutil
import random
from typing import List, Dict, Any
from datetime import datetime
from backend.app.ingestion.base import SourceConnector
from backend.app.ingestion.dto import AudioInput
from backend.app.core.logging import get_logger

logger = get_logger("INGESTION")

class DialerAdapter:
    """
    Adapter interface simulating real-world Dialer systems (Five9, Salesforce Dialer, Vicidial).
    """
    def __init__(self, vendor: str, credentials: Dict[str, str] = None):
        self.vendor = vendor
        self.creds = credentials or {}

    def retrieve_call_file(self, lead_id: str, target_path: str) -> bool:
        # For simulation, copy a local synthetic file
        src_opts = [
            "good call recording synthetic data.mp3",
            "bad-score call recording synethetic data.mp3"
        ]
        filename = random.choice(src_opts)
        src_path = os.path.join("C:/Users/Admin/Desktop/novafit", filename)
        
        if not os.path.exists(src_path):
            src_path = filename
            
        if os.path.exists(src_path):
            shutil.copy2(src_path, target_path)
            logger.info(f"Dialer simulator: Retrieved lead call audio {filename} to {target_path}")
            return True
            
        logger.error(f"Dialer simulator could not find synthetic source audio at {src_path}")
        return False

class DialerConnector(SourceConnector):
    """
    Ingestion connector for outbound dialer platforms (Five9, Salesforce, Vicidial).
    """
    def __init__(self, vendor: str, config: Dict[str, Any] = None):
        self.vendor = vendor
        self.config = config or {}
        self.adapter = DialerAdapter(vendor, self.config.get("credentials"))

    def connect(self) -> bool:
        return True

    def validate(self) -> bool:
        return True

    def fetch(self) -> List[AudioInput]:
        lead_id = f"LD{random.randint(1000, 9999)}"
        call_id = f"DL{random.randint(100000, 999999)}"
        
        # Temp folder
        temp_dir = "./storage/temp_dialer"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.abspath(os.path.join(temp_dir, f"{self.vendor.lower()}_{call_id}.mp3"))
        
        retrieved = self.adapter.retrieve_call_file(lead_id, temp_file_path)
        if not retrieved:
            raise RuntimeError(f"Failed to fetch dialer recording from {self.vendor}")
            
        raw_dialer_data = {
            "audio_path": temp_file_path,
            "original_filename": f"{self.vendor.lower()}_{call_id}.mp3",
            "mime_type": "audio/mp3",
            "external_call_id": call_id,
            "lead_id": lead_id,
            "campaign": "FitNova New Year Transformation Outbound",
            "disposition": "Answering Machine/Pitch Competed" if "bad-score" in temp_file_path else "Interested/Closed",
            "timestamp": datetime.now().isoformat()
        }
        
        audio_input = self.normalize(raw_dialer_data)
        return [audio_input]

    def normalize(self, raw_data: dict) -> AudioInput:
        customer = random.choice(["Neha", "Rohan", "Amit", "Rahul", "Priya"])
        advisor = random.choice(["Arjun", "Rahul", "Priya", "Vikram", "Simran"])
        
        return AudioInput(
            source="Dialer",
            vendor=self.vendor,
            audio_path=raw_data["audio_path"],
            original_filename=raw_data["original_filename"],
            mime_type=raw_data["mime_type"],
            duration=0.0,
            call_time=raw_data["timestamp"],
            external_call_id=raw_data["external_call_id"],
            customer_name=customer,
            advisor_name=advisor,
            metadata={
                "dialer_lead_id": raw_data["lead_id"],
                "dialer_campaign": raw_data["campaign"],
                "dialer_disposition": raw_data["disposition"],
                "direction": "Outbound"
            }
        )
