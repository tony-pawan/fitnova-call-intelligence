from pydantic import Field  # pyrefly: ignore [missing-import]
from backend.app.schemas.common import BaseSchema, TimestampSchema

class TeamBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255, description="Team name (non-empty)")
    organization_id: int

class TeamCreate(TeamBase):
    pass

class TeamUpdate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)

class Team(TeamBase, TimestampSchema):
    id: int
