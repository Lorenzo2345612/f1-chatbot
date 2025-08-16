from pydantic import BaseModel
from typing import Literal, List

class ChatMessageRequest(BaseModel):
    content: str

class ChatResponse(BaseModel):
    response: str

class LLMResponse(BaseModel):
    query: str