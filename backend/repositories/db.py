from abc import ABC, abstractmethod
import re
from typing import Tuple, List
from schemas.db import MatchData
from models.deps import get_db
from sqlalchemy import text

class DBBaseRepository(ABC):
    @abstractmethod
    async def execute_query(self, query: str, params: dict = None):
        """Ejecuta una consulta en la base de datos"""
        pass

class PostgresRepository(DBBaseRepository):
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # Aquí podrías inicializar la conexión a la base de datos

    async def execute_query(self, query: str, params: dict = None):
        async with get_db() as session:
            result = await session.execute(
                text(query),
                params or {}
            )
            return result.fetchall()


class QueryCleaner:
    counter = 0
    extracted_data = []
    def replace_meeting_counter(self, match, sql_key, key_prefix, type_name):
        self.counter += 1
        name = match.group(1)
        self.extracted_data.append(MatchData(type=type_name, key=f"{key_prefix}_{self.counter}", data=name))
        return f"{sql_key} = :{key_prefix}_{self.counter}"
    
    def clean_driver_info(self, query: str) -> Tuple[str, List[MatchData]]:
        """Limpia la consulta relacionada con la información de conductores."""
        # Patern to replace "full_name = 'name of driver'" 
        counter = 0
        extracted_data = []
        def replace_driver_counter(match):
            nonlocal counter
            counter += 1
            driver_name = match.group(1)
            extracted_data.append(MatchData(type="driver_full_name", key=f"driver_{counter}", data=driver_name))
            return f"full_name = :driver_{counter}"
        cleaned_query = re.sub(r"full_name\s?=\s?'([^']+)'", replace_driver_counter, query)

        # Replace "name_acronym = 'acronym of driver'"
        counter = 0
        def replace_acronym_counter(match):
            nonlocal counter
            counter += 1
            acronym = match.group(1)
            extracted_data.append(MatchData(type="driver_acronym", key=f"acronym_{counter}", data=acronym))
            return f"name_acronym = :acronym_{counter}"
        
        cleaned_query = re.sub(r"name_acronym\s?=\s?'([^']+)'", replace_acronym_counter, cleaned_query)

        return cleaned_query, extracted_data
    
    def clean_meeting_info(self, query: str) -> Tuple[str, List[MatchData]]:
        """Cleans the query related to meeting information."""
        counter = 0
        extracted_data = []
        
        def replace_meeting_counter(match):
            nonlocal counter
            counter += 1
            meeting_name = match.group(1)
            extracted_data.append(MatchData(type="meeting_name", key=f"meeting_{counter}", data=meeting_name))
            return f"meeting_official_name = :meeting_{counter}"
        
        cleaned_query = re.sub(r"meeting_official_name\s?=\s?'([^']+)'", replace_meeting_counter, query)

        # Replace "location = 'location of meeting'"
        counter = 0
        def replace_location_counter(match):
            nonlocal counter
            counter += 1
            location_name = match.group(1)
            extracted_data.append(MatchData(type="meeting_location", key=f"location_{counter}", data=location_name))
            return f"location = :location_{counter}"
        cleaned_query = re.sub(r"location\s?=\s?'([^']+)'", replace_location_counter, cleaned_query)

        # Replace meeting_standard_name
        counter = 0
        def replace_standard_name_counter(match):
            nonlocal counter
            counter += 1
            standard_name = match.group(1)
            extracted_data.append(MatchData(type="meeting_standard_name", key=f"standard_name_{counter}", data=standard_name))
            return f"meeting_standard_name = :standard_name_{counter}"
        cleaned_query = re.sub(r"meeting_standard_name\s?=\s?'([^']+)'", replace_standard_name_counter, cleaned_query)

        return cleaned_query, extracted_data
    
    def clean_session_info(self, query: str) -> Tuple[str, List[MatchData]]:
        """Cleans the query related to session information."""
        counter = 0
        extracted_data = []
        
        def replace_session_counter(match):
            nonlocal counter
            counter += 1
            session_name = match.group(1)
            extracted_data.append(MatchData(type="session_name", key=f"session_{counter}", data=session_name))
            return f"session_name = :session_{counter}"
        
        cleaned_query = re.sub(r"session_name\s?=\s?'([^']+)'", replace_session_counter, query)

        # Replace "session_type = 'type of session'"
        counter = 0
        def replace_session_type_counter(match):
            nonlocal counter
            counter += 1
            session_type = match.group(1)
            extracted_data.append(MatchData(type="session_type", key=f"session_type_{counter}", data=session_type))
            return f"session_type = :session_type_{counter}"
        
        cleaned_query = re.sub(r"session_type\s?=\s?'([^']+)'", replace_session_type_counter, cleaned_query)

        return cleaned_query, extracted_data
    
    def clean_stint_info(self, query: str) -> Tuple[str, List[MatchData]]:
        """Cleans the query related to stint information."""
        extracted_data = []
        
        # Replace "compound = 'compound of tyre'"
        counter = 0
        def replace_compound_counter(match):
            nonlocal counter
            counter += 1
            compound_name = match.group(1)
            extracted_data.append(MatchData(type="tyre_compound", key=f"compound_{counter}", data=compound_name))
            return f"compound = :compound_{counter}"
        
        # Initialize cleaned_query from the input query (bug fix)
        cleaned_query = re.sub(r"compound\s?=\s?'([^']+)'", replace_compound_counter, query)

        return cleaned_query, extracted_data
    
    def clean_query(self, query: str) -> Tuple[str, List[MatchData]]:
        """Limpia la consulta SQL y extrae datos relevantes."""
        query = query.strip()
        extracted_data = []

        # Limpiar información de conductores
        query, driver_data = self.clean_driver_info(query)
        extracted_data.extend(driver_data)

        # Limpiar información de reuniones
        query, meeting_data = self.clean_meeting_info(query)
        extracted_data.extend(meeting_data)

        # Limpiar información de sesiones
        query, session_data = self.clean_session_info(query)
        extracted_data.extend(session_data)

        # Limpiar información de stints
        query, stint_data = self.clean_stint_info(query)
        extracted_data.extend(stint_data)

        return query, extracted_data
        
        
        
        