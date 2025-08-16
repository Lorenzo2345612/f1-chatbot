from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from typing import Any
import asyncio
from repositories.db import DBBaseRepository, QueryCleaner
from repositories.user_chat_history import BaseRepository
from repositories.qdrant_service import QdrantRepository
from prompts.user_question_to_response import PROMPT_REQUEST_TO_SQL, PROMPT_INTERPRET_SQL_RESULTS
from utils.logger import logger
import re

def extract_sql(text: str) -> str:
    # Deletes ```sql ... ``` if exists
    match = re.search(r"```sql\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()

def debug_prompt(prompt: str):
    """Debugging function to print the prompt."""
    logger.debug(f"Prompt: {prompt}")
    return prompt

class NLToSQLInterpreter:
    def __init__(self, db_repo: DBBaseRepository, history_repo: BaseRepository, query_cleaner: QueryCleaner, qdrant_repo: QdrantRepository, model_name: str = "gemini-1.5-flash"):
        self.db_repo = db_repo
        self.history_repo = history_repo
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0)
        self.query_cleaner = query_cleaner
        self.qdrant_repo = qdrant_repo

    def _get_history_as_messages(self, user_id: str):
        """Convierte historial guardado en objetos HumanMessage y AIMessage"""
        return self.history_repo.get_chat_history(user_id)
    
    def _get_humman_messages(self, user_id: str):
        """Obtiene solo los mensajes de usuario del historial"""
        return self.history_repo.get_human_chat_history(user_id)

    def request_to_sql(self, user_id: str, natural_language_question: str) -> str:
        history_messages = self._get_history_as_messages(user_id)
        chain = PROMPT_REQUEST_TO_SQL | RunnableLambda(debug_prompt) | self.llm | StrOutputParser() | (lambda x: extract_sql(x))
        sql_query = chain.invoke({
            "history": history_messages,
            "input": natural_language_question
        }).strip()
        return sql_query

    def interpret_results(self, user_id: str, question: str, results: Any) -> str:
        history_messages = self._get_history_as_messages(user_id)
        chain = PROMPT_INTERPRET_SQL_RESULTS | self.llm
        interpretation = chain.invoke({
            "history": history_messages,
            "question": question,
            "results": results
        }).content.strip()
        return interpretation

    async def _fetch_param(self, data_item):
        """Obtiene el parámetro real desde Qdrant para un item extraído.
        Devuelve una tupla (key, value) con fallback al valor original en caso de error o sin resultados.
        """
        try:
            results = await self.qdrant_repo.similarity_search_async(
                collection_name=data_item.type,
                search_query=data_item.data,
                limit=1
            )
            if results:
                top = results[0]
                payload = getattr(top, "payload", None) or {}
                value = payload.get("text") or payload.get("value") or next(iter(payload.values()), None)
                return data_item.key, (value if value is not None else data_item.data)
            return data_item.key, data_item.data
        except Exception:
            return data_item.key, data_item.data

    async def run_query_flow(self, user_id: str, question: str) -> str:
        # Save user message
        self.history_repo.set_next_chat_message(user_id, f"{question}", type="user")

        # Step 1: Question → SQL
        sql_query = self.request_to_sql(user_id, question)

        try:
            # Step 2: Clean SQL query
            cleaned_query, extracted_data = self.query_cleaner.clean_query(sql_query)

            # Step 3: Get real params from qdrant (concurrent)
            params = {}
            if extracted_data:
                fetched = await asyncio.gather(*(self._fetch_param(d) for d in extracted_data))
                params = {k: v for k, v in fetched}

            # Step 4: Execute SQL
            query_results = await self.db_repo.execute_query(cleaned_query, params)
        except Exception as e:
            logger.error(f"Error executing query for user {user_id}: {str(e)}")
            query_results = []

        # Step 5: Interpret results
        interpretation = self.interpret_results(user_id, question, query_results)

        # Save system response
        self.history_repo.set_next_chat_message(user_id, f"{interpretation}", type="system")

        return interpretation
