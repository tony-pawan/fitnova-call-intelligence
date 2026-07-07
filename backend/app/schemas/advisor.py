import re
from pydantic import Field, field_validator  # pyrefly: ignore [missing-import]
from backend.app.schemas.common import BaseSchema, TimestampSchema

# Robust RFC-like regex for basic email verification
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

class AdvisorBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=255, description="Advisor name (non-empty)")
    email: str = Field(..., description="Advisor email address")
    team_id: int

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        normalized_email = v.strip()
        if not EMAIL_REGEX.match(normalized_email):
            raise ValueError("Invalid email formatting: must be a valid email address.")
        return normalized_email

class AdvisorCreate(AdvisorBase):
    pass

class AdvisorUpdate(BaseSchema):
    name: str = Field(None, min_length=1, max_length=255)
    email: str = Field(None)
    team_id: int = Field(None)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        if v is None:
            return v
        normalized_email = v.strip()
        if not EMAIL_REGEX.match(normalized_email):
            raise ValueError("Invalid email formatting: must be a valid email address.")
        return normalized_email

class Advisor(AdvisorBase, TimestampSchema):
    id: int
