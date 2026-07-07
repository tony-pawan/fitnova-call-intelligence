from fastapi import APIRouter  # pyrefly: ignore [missing-import]
from backend.app.api.routes import health, calls, advisors, appeals

api_router = APIRouter()

# Include routes
api_router.include_router(health.router)
api_router.include_router(calls.router)
api_router.include_router(advisors.router)
api_router.include_router(appeals.router)
