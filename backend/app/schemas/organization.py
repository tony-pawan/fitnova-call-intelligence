from pydantic import Field  # pyrefly: ignore [missing-import]
from backend.app.schemas.common import BaseSchema, TimestampSchema

class OrganizationBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255, description="Organization name (non-empty)")

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255)

class Organization(OrganizationBase, TimestampSchema):
    id: int
