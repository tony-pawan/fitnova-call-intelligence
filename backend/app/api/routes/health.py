from fastapi import APIRouter  # pyrefly: ignore [missing-import]

router = APIRouter()

@router.get("/health", tags=["Health"])
def health_check():
    """
    Simple health check endpoint returning the status of the API.
    """
    return {"status": "healthy"}
