from fastapi import APIRouter  # pyrefly: ignore [missing-import]
from backend.app.api.routes import health, calls, org_team_advisor

api_router = APIRouter()

# Include routes
api_router.include_router(health.router)
api_router.include_router(calls.router)
api_router.include_router(org_team_advisor.router)
