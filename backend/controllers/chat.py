from fastapi import APIRouter, HTTPException
from services.chat import ChatService
from repositories.lang_chain import NLToSQLInterpreter
from repositories.db import PostgresRepository, QueryCleaner
from repositories.user_chat_history import UserChatHistoryRepository, RedisChatHistoryRepository
from repositories.qdrant_service import QdrantRepository
from schemas.chat import ChatMessageRequest, ChatResponse
from constants.db import DATABASE_URL, QDRANT_URL
from utils.logger import logger

# Initialize repositories and services
db_repo = PostgresRepository(DATABASE_URL)
history_repo = RedisChatHistoryRepository()  
query_cleaner = QueryCleaner()
qdrant_repo = QdrantRepository(url=QDRANT_URL)

# Initialize the NLToSQLInterpreter with the repositories
nlsql_interpreter = NLToSQLInterpreter(
    db_repo=db_repo,
    history_repo=history_repo,
    query_cleaner=query_cleaner,
    qdrant_repo=qdrant_repo,
    model_name="gemini-2.0-flash"
)

# Initialize the ChatService with the NLToSQLInterpreter
service = ChatService(
    lang_chain=nlsql_interpreter
)

chat_router = APIRouter()

@chat_router.post("/chat/{user_id}", response_model=ChatResponse)
async def chat_with_user(user_id: str, request: ChatMessageRequest):
    """Endpoint to handle chat messages from users."""
    try:
        response = await service.chat(request, user_id)
        return response
    except Exception as e:
        logger.error(f"Error processing chat for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing the chat: {str(e)}"
        )
