from fastapi import APIRouter, HTTPException
import uuid

user_router = APIRouter()


@user_router.post("/request-session", response_model=str)
async def request_session():
    """Endpoint to request a new user session."""
    try:
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        return session_id
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while requesting a session: {str(e)}"
        )
