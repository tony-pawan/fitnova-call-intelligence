from fastapi import FastAPI  # pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware  # pyrefly: ignore [missing-import]
from backend.app.core.config import settings
from backend.app.core.logging import setup_logging, get_logger
from backend.app.api.router import api_router

# Initialize structured console logger prior to app instantiation
setup_logging(settings.LOG_LEVEL)
logger = get_logger("SYSTEM")

logger.info(f"Starting FitNova Sales Call Intelligence API (Log Level: {settings.LOG_LEVEL})")

# Instantiate FastAPI application
app = FastAPI(
    title="FitNova Sales Call Intelligence System",
    description="Backend API for sales call recording uploads, automatic transcription, diarization, and Gemini conversation intelligence analytics.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Set up CORS middleware for integration with the Streamlit client or local dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to Streamlit URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register central routers
app.include_router(api_router)

@app.on_event("startup")
def on_startup() -> None:
    from backend.app.database.init_db import init_db
    try:
        init_db()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    logger.info("FitNova API started successfully. Access Swagger documentation at http://localhost:8000/docs")

@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("FitNova API shutting down...")

# Trigger auto-reload to terminate active background processing threads cleanly (Hot-reload config triggered)
