from sqlalchemy.orm import DeclarativeBase  # pyrefly: ignore [missing-import]

class Base(DeclarativeBase):
    """
    SQLAlchemy DeclarativeBase using 2.0 style mapping.
    All database models should inherit from this base class.
    """
    pass
