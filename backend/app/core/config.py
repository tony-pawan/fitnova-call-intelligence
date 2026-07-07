import os
from pydantic import Field  # pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict  # pyrefly: ignore [missing-import]

class Settings(BaseSettings):
    """
    Application settings model using Pydantic V2 settings management.
    Loads variables from the environment and falls back to .env files or defaults.
    """
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/fitnova",
        description="Database URL for PostgreSQL connection."
    )
    GEMINI_API_KEY: str = Field(
        default="mock_key_for_development",
        description="Google Gemini API Key."
    )
    UPLOAD_FOLDER: str = Field(
        default="./storage/audio",
        description="Folder path where uploaded audio recordings are saved."
    )
    TRANSCRIPT_FOLDER: str = Field(
        default="./storage/transcripts",
        description="Folder path where raw and generated transcriptions are saved."
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Global application log level."
    )

    # Faster Whisper parameters
    WHISPER_MODEL: str = Field(
        default="base",
        description="Faster Whisper model identifier size (e.g. tiny, base, small, medium)."
    )
    WHISPER_DEVICE: str = Field(
        default="cpu",
        description="Execution device mapping for Faster Whisper (e.g. cpu or cuda)."
    )
    WHISPER_COMPUTE_TYPE: str = Field(
        default="int8",
        description="Compute quantization type for performance optimization (e.g. int8, float16)."
    )

    # Speaker Diarization parameters
    PYANNOTE_MODEL: str = Field(
        default="pyannote/speaker-diarization-3.1",
        description="Hugging Face repo ID for Pyannote speaker diarization."
    )
    PYANNOTE_AUTH_TOKEN: str = Field(
        default="",
        description="Hugging Face auth token for pyannote downloads."
    )
    PYANNOTE_DEVICE: str = Field(
        default="cpu",
        description="Device mapping for pyannote (cpu or cuda)."
    )
    CONVERSATION_FOLDER: str = Field(
        default="./storage/conversations",
        description="Folder path where reconstructed conversations are saved."
    )

    # Gemini LLM parameters
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-flash",
        description="Google Gemini model identifier (e.g. gemini-1.5-flash, gemini-1.5-pro)."
    )
    TEMPERATURE: float = Field(
        default=0.2,
        description="Sampling temperature for LLM responses (creativity vs. deterministic)."
    )
    MAX_OUTPUT_TOKENS: int = Field(
        default=1024,
        description="Maximum tokens allowed in generative AI response."
    )
    ANALYSIS_FOLDER: str = Field(
        default="./storage/analysis",
        description="Folder path where generated analysis scorecards are saved."
    )

    # Use pydantic-settings config to read .env file
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
