from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from backend.app.schemas.common import BaseSchema, TimestampSchema

# --- Organization ---
class OrganizationBase(BaseModel):
    name: str

class OrganizationCreate(OrganizationBase):
    pass

class Organization(OrganizationBase, TimestampSchema):
    id: int

# --- Team ---
class TeamBase(BaseModel):
    name: str
    organization_id: int

class TeamCreate(TeamBase):
    pass

class Team(TeamBase, TimestampSchema):
    id: int

# --- Advisor ---
class AdvisorBase(BaseModel):
    name: str
    team_id: int
    employee_code: str
    email: Optional[str] = None

class AdvisorCreate(AdvisorBase):
    pass

class Advisor(AdvisorBase, TimestampSchema):
    id: int

# --- Ingestion Source ---
class IngestionSourceBase(BaseModel):
    name: str
    type: str
    configuration_json: Optional[str] = None
    enabled: Optional[bool] = True

class IngestionSourceCreate(IngestionSourceBase):
    pass

class IngestionSource(IngestionSourceBase, TimestampSchema):
    id: int
