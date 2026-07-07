from datetime import datetime
from pydantic import BaseModel, ConfigDict  # pyrefly: ignore [missing-import]

class BaseSchema(BaseModel):
    """
    Base schema configuring from_attributes=True to allow
    compatibility with ORM models.
    """
    model_config = ConfigDict(from_attributes=True)

class TimestampSchema(BaseSchema):
    """
    Mixin-like schema providing standardized created_at/updated_at fields.
    """
    created_at: datetime
    updated_at: datetime
