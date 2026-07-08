import os
import csv
from typing import List, Dict, Any
from backend.app.ingestion.base import SourceConnector
from backend.app.ingestion.dto import AudioInput
from backend.app.core.logging import get_logger

logger = get_logger("INGESTION")

class CRMConnector(SourceConnector):
    """
    Ingestion connector for parsing customer relationship management dataset exports (CSV/Excel).
    Maps exported recording files inside a local folder with their metadata.
    """
    def __init__(self, metadata_file_path: str, audio_directory_path: str):
        self.metadata_path = metadata_file_path
        self.audio_dir = audio_directory_path
        self.rows: List[Dict[str, str]] = []

    def connect(self) -> bool:
        if not os.path.exists(self.metadata_path):
            logger.error(f"CRM metadata file not found at: {self.metadata_path}")
            return False
        if not os.path.exists(self.audio_dir) or not os.path.isdir(self.audio_dir):
            logger.error(f"CRM audio recordings directory not found at: {self.audio_dir}")
            return False
        return True

    def validate(self) -> bool:
        if not self.connect():
            return False
            
        ext = os.path.splitext(self.metadata_path)[1].lower()
        if ext not in [".csv", ".xlsx", ".xls"]:
            logger.error(f"Unsupported CRM metadata format: {ext}")
            return False
            
        return True

    def fetch(self) -> List[AudioInput]:
        if not self.validate():
            raise ValueError("CRM ingestion validation failed.")
            
        ext = os.path.splitext(self.metadata_path)[1].lower()
        if ext == ".csv":
            self._parse_csv()
        else:
            self._parse_excel()
            
        logger.info(f"Parsed {len(self.rows)} rows from CRM metadata sheet.")
        
        audio_inputs = []
        for idx, row in enumerate(self.rows):
            filename = row.get("filename", "").strip()
            if not filename:
                logger.warning(f"Row {idx} missing 'filename' field. Skipping.")
                continue
                
            audio_path = os.path.join(self.audio_dir, filename)
            if not os.path.exists(audio_path):
                logger.warning(f"Audio file '{filename}' mapped on row {idx} does not exist in target audio folder. Skipping.")
                continue
                
            # Determine MIME type
            file_ext = os.path.splitext(filename)[1].lower()
            mime_type = "audio/mpeg" if file_ext == ".mp3" else (
                "audio/wav" if file_ext == ".wav" else f"audio/{file_ext[1:]}"
            )
            
            normalized_dto = self.normalize({
                "audio_path": audio_path,
                "original_filename": filename,
                "mime_type": mime_type,
                "row_metadata": row
            })
            audio_inputs.append(normalized_dto)
            
        return audio_inputs

    def normalize(self, raw_data: dict) -> AudioInput:
        row = raw_data["row_metadata"]
        
        # Pull typical CRM metadata fields
        customer = row.get("customer_name") or row.get("Customer Name") or row.get("customer")
        advisor = row.get("advisor_name") or row.get("Advisor Name") or row.get("advisor") or row.get("agent")
        call_id = row.get("external_call_id") or row.get("Call ID") or row.get("call_id") or row.get("id")
        call_time = row.get("call_time") or row.get("Call Time") or row.get("timestamp") or row.get("date")
        
        # Clean dict
        clean_meta = {k: v for k, v in row.items() if k not in ["filename"]}
        
        return AudioInput(
            source="CRM",
            vendor=row.get("vendor", "CRM Dataset Export"),
            audio_path=raw_data["audio_path"],
            original_filename=raw_data["original_filename"],
            mime_type=raw_data["mime_type"],
            duration=0.0,
            call_time=call_time,
            external_call_id=call_id,
            customer_name=customer,
            advisor_name=advisor,
            metadata=clean_meta
        )

    def _parse_csv(self):
        try:
            with open(self.metadata_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                self.rows = [dict(row) for row in reader]
        except Exception as e:
            logger.error(f"Failed to parse CRM CSV file: {e}")
            raise RuntimeError(f"CRM CSV parsing failure: {e}")

    def _parse_excel(self):
        try:
            # Fallback to importing pandas/openpyxl dynamically.
            # If not installed, raise exception.
            import pandas as pd
            df = pd.read_excel(self.metadata_path)
            # Replace NaN with empty strings
            df = df.fillna("")
            self.rows = df.to_dict(orient="records")
            # Convert all keys/values to strings for normalization consistency
            self.rows = [{str(k): str(v) for k, v in row.items()} for row in self.rows]
        except ImportError:
            msg = "CRM Excel ingestion (.xlsx/.xls) requires 'pandas' and 'openpyxl' dependencies. Please install them or use a standard CSV file."
            logger.error(msg)
            raise ImportError(msg)
        except Exception as e:
            logger.error(f"Failed to parse CRM Excel file: {e}")
            raise RuntimeError(f"CRM Excel parsing failure: {e}")
