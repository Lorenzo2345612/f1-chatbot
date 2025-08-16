from schemas.chat import ChatMessageRequest, ChatResponse
from repositories.lang_chain import NLToSQLInterpreter
class ChatService:
    def __init__(self, lang_chain: NLToSQLInterpreter):
        self.lang_chain = lang_chain

    async def chat(self, message: ChatMessageRequest, user_id: str) -> ChatResponse:
        """Process a chat message and return a response."""
        # Convert the natural language question to SQL
        response = await self.lang_chain.run_query_flow(user_id, message.content)
        return ChatResponse(response=response)
