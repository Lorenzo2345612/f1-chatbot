from pydantic import BaseModel

class MatchData(BaseModel):
    """Model to represent match data."""
    type: str
    key: str
    data: str