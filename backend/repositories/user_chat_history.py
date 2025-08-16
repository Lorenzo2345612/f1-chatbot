from abc import ABC, abstractmethod
from constants.db import REDIS_URL
from langchain_community.chat_message_histories import RedisChatMessageHistory
from utils.logger import logger
from langchain_core.messages import HumanMessage

class BaseRepository(ABC):
    @abstractmethod
    def set_next_chat_message(self, user_id: str, message: str, type: str = "user"):
        """Establece el siguiente mensaje de chat para un usuario"""
        pass

    @abstractmethod
    def get_chat_history(self, user_id: str, limit: int = 10) -> list:
        """Obtiene el historial de chat de un usuario"""
        pass

    @abstractmethod
    def get_human_chat_history(self, user_id: str, limit: int = 10) -> list:
        """Obtiene solo los mensajes de usuario del historial"""
        pass

class UserChatHistoryRepository:
    history = dict()

    def set_next_chat_message(self, user_id: str, message: str):
        """Establece el siguiente mensaje de chat para un usuario"""
        if user_id not in self.history:
            self.history[user_id] = []
        self.history[user_id].append(message)

    def get_chat_history(self, user_id: str) -> list:
        """Obtiene el historial de chat de un usuario"""
        return self.history.get(user_id, [])
    
    def get_human_chat_history(self, user_id: str) -> list:
        """Obtiene solo los mensajes de usuario del historial"""
        return [msg for msg in self.history.get(user_id, []) if isinstance(msg, HumanMessage)]
    
class RedisChatHistoryRepository(BaseRepository):
    def set_next_chat_message(self, user_id: str, message: str, type: str = "user"):
        """Establece el siguiente mensaje de chat para un usuario en Redis"""
        history = RedisChatMessageHistory(
            session_id=user_id,
            url=REDIS_URL 
        )
        if type == "user":
            history.add_user_message(message)
        else:
            history.add_ai_message(message)

    def get_chat_history(self, user_id: str, limit: int = 10) -> list:
        """Obtiene el historial de chat de un usuario desde Redis"""
        history = RedisChatMessageHistory(
            session_id=user_id,
            url=REDIS_URL 
        )
        return history.messages[-limit:] if limit > 0 else history.messages
    
    def get_human_chat_history(self, user_id: str, limit: int = 10) -> list:
        """Obtiene solo los mensajes de usuario del historial en Redis"""
        history = RedisChatMessageHistory(
            session_id=user_id,
            url=REDIS_URL 
        )
        user_messages = [msg for msg in history.messages if isinstance(msg, HumanMessage)]
        return user_messages[-limit:] if limit > 0 else user_messages
        