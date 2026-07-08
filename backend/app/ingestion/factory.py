from backend.app.ingestion.connectors.upload_connector import UploadConnector
from backend.app.ingestion.connectors.folder_connector import FolderConnector
from backend.app.ingestion.connectors.crm_connector import CRMConnector
from backend.app.ingestion.connectors.api_connector import APIConnector
from backend.app.ingestion.connectors.telephony_connector import TelephonyConnector
from backend.app.ingestion.connectors.dialer_connector import DialerConnector

class ConnectorFactory:
    """
    Factory class responsible for instantiating the correct SourceConnector.
    """
    @staticmethod
    def get_connector(source_type: str, **kwargs):
        src_lower = source_type.lower()
        if src_lower == "upload":
            return UploadConnector(
                filename=kwargs.get("filename"),
                temp_path=kwargs.get("temp_path"),
                size_bytes=kwargs.get("size_bytes"),
                metadata=kwargs.get("metadata"),
                organization_id=kwargs.get("organization_id"),
                team_id=kwargs.get("team_id"),
                advisor_id=kwargs.get("advisor_id"),
                source_id=kwargs.get("source_id")
            )
        elif src_lower == "folder":
            return FolderConnector(
                folder_path=kwargs.get("folder_path"),
                db=kwargs.get("db")
            )
        elif src_lower == "crm":
            return CRMConnector(
                metadata_file_path=kwargs.get("metadata_file_path"),
                audio_directory_path=kwargs.get("audio_directory_path")
            )
        elif src_lower == "api":
            return APIConnector(
                filename=kwargs.get("filename"),
                temp_path=kwargs.get("temp_path"),
                external_call_id=kwargs.get("external_call_id"),
                metadata=kwargs.get("metadata")
            )
        elif src_lower == "telephony":
            return TelephonyConnector(
                vendor=kwargs.get("vendor", "Twilio"),
                config=kwargs.get("config")
            )
        elif src_lower == "dialer":
            return DialerConnector(
                vendor=kwargs.get("vendor", "Five9"),
                config=kwargs.get("config")
            )
        else:
            raise ValueError(f"Unknown ingestion source type: {source_type}")
