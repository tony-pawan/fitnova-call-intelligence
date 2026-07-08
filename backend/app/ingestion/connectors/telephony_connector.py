import os
import shutil
import random
from typing import List, Dict, Any
from datetime import datetime
from backend.app.ingestion.base import SourceConnector
from backend.app.ingestion.dto import AudioInput
from backend.app.core.logging import get_logger

logger = get_logger("INGESTION")

class TelephonyAdapter:
    """
    Adapter interface simulating real-world telephony API connection layouts.
    In production, this would make HTTP requests to Twilio/Aircall webhook events or retrieve recordings via S3 buckets.
    """
    def __init__(self, vendor: str, credentials: Dict[str, str] = None):
        self.vendor = vendor
        self.creds = credentials or {}

    def fetch_recording_url(self, call_sid: str) -> str:
        # Mimics fetching the direct audio stream URL from the provider API
        return f"https://api.{self.vendor.lower()}.com/v1/Accounts/AC123/Recordings/{call_sid}.mp3"

    def download_recording(self, call_sid: str, target_path: str) -> bool:
        # In a real integration, this downloads the audio file from the telephony provider to local disk
        # For the simulator, we copy one of our synthetic files to mimic a download.
        src_opts = [
            "good call recording synthetic data.mp3",
            "bad-score call recording synethetic data.mp3"
        ]
        
        # Pick one randomly or default to good
        filename = random.choice(src_opts)
        src_path = os.path.join("C:/Users/Admin/Desktop/novafit", filename)
        
        if not os.path.exists(src_path):
            # Fallback search in parent directory or current run path
            src_path = filename
            
        if os.path.exists(src_path):
            shutil.copy2(src_path, target_path)
            logger.info(f"Telephony simulator: Downloaded mock audio stream {filename} to {target_path}")
            return True
            
        logger.error(f"Telephony simulator could not find synthetic source audio at {src_path}")
        return False

class TelephonyConnector(SourceConnector):
    """
    Ingestion connector for telephony platforms (Twilio, Aircall, RingCentral, Genesys, CloudTalk, Dialpad).
    """
    def __init__(self, vendor: str, config: Dict[str, Any] = None):
        self.vendor = vendor
        self.config = config or {}
        self.adapter = TelephonyAdapter(vendor, self.config.get("credentials"))

    def connect(self) -> bool:
        # Validates config credentials
        api_key = self.config.get("api_key") or self.config.get("credentials", {}).get("api_key")
        if not api_key:
            logger.warning(f"Telephony credentials missing for {self.vendor}. Initializing in simulation mode.")
        return True

    def validate(self) -> bool:
        return True

    def fetch(self) -> List[AudioInput]:
        # Generate a simulated call event payload
        call_sid = f"CA{random.randint(100000, 999999)}abc{random.randint(10, 99)}"
        
        # Create temp folder for downloads
        temp_dir = "./storage/temp_telephony"
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.abspath(os.path.join(temp_dir, f"{self.vendor.lower()}_{call_sid}.mp3"))
        
        # Download (Copy) file
        downloaded = self.adapter.download_recording(call_sid, temp_file_path)
        if not downloaded:
            raise RuntimeError(f"Failed to fetch telephony recording from {self.vendor}")
            
        # Build normalized input DTO
        raw_telephony_data = {
            "audio_path": temp_file_path,
            "original_filename": f"{self.vendor.lower()}_{call_sid}.mp3",
            "mime_type": "audio/mp3",
            "call_sid": call_sid,
            "customer_phone": f"+1555{random.randint(1000000, 9999999)}",
            "advisor_extension": f"ext-{random.randint(100, 999)}",
            "timestamp": datetime.now().isoformat()
        }
        
        audio_input = self.normalize(raw_telephony_data)
        return [audio_input]

    def normalize(self, raw_data: dict) -> AudioInput:
        # Simulated customer/advisor assignments for the simulation run
        customer = random.choice(["Neha", "Rohan", "Amit", "Rahul", "Priya"])
        advisor = random.choice(["Arjun", "Rahul", "Priya", "Vikram", "Simran"])
        
        return AudioInput(
            source="Telephony",
            vendor=self.vendor,
            audio_path=raw_data["audio_path"],
            original_filename=raw_data["original_filename"],
            mime_type=raw_data["mime_type"],
            duration=0.0,
            call_time=raw_data["timestamp"],
            external_call_id=raw_data["call_sid"],
            customer_name=customer,
            advisor_name=advisor,
            metadata={
                "telephony_call_sid": raw_data["call_sid"],
                "customer_phone": raw_data["customer_phone"],
                "advisor_extension": raw_data["advisor_extension"],
                "channel": "Voice Call",
                "direction": "Inbound"
            }
        )
