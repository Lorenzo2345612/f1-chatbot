from dotenv import load_dotenv
load_dotenv()
import asyncio
import fastf1
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from models.db import async_session
from models.models import (
    Season, Meeting, Session, Driver, SessionDriver, SessionResult,
    Stint, Lap, PitStop, StartGrid, PointsScored
)
from models.db import engine, Base

# Enable FastF1 cache for better performance
fastf1.Cache.enable_cache('tmp')

class F1DataImporter:
    def __init__(self):
        self.session_type_mapping = {
            'FP1': 'Practice 1',
            'FP2': 'Practice 2', 
            'FP3': 'Practice 3',
            'Q': 'Qualifying',
            'SQ': 'Sprint Qualifying',
            'S': 'Sprint',
            'R': 'Race'
        }
        
    async def import_season(self, year: int):
        """Import a complete season"""
        print(f"Starting import for {year} season...")
        
        schedule = fastf1.get_event_schedule(year)
        
        async with async_session() as session:
            # Insert season
            season_obj = await self.get_or_create_season(session, year)
            
            for _, event in schedule.iterrows():
                if pd.isna(event['EventDate']):
                    continue
                    
                print(f"Processing {event['EventName']} ({event['Country']})...")
                
                try:
                    # Insert meeting
                    meeting_obj = await self.get_or_create_meeting(session, event, season_obj.id)
                    
                    # Process all sessions for this event
                    await self.process_event_sessions(session, year, event, meeting_obj.id)
                    
                    await session.commit()
                    print(f"✓ Completed {event['EventName']}")
                    
                except Exception as e:
                    print(f"✗ Error processing {event['EventName']}: {str(e)}")
                    await session.rollback()
                    continue
    
    async def get_or_create_season(self, session, year: int) -> Season:
        """Get or create season"""
        stmt = select(Season).where(Season.year == year)
        result = await session.execute(stmt)
        season_obj = result.scalar_one_or_none()
        
        if not season_obj:
            season_obj = Season(year=year)
            session.add(season_obj)
            await session.flush()
        
        return season_obj
    
    async def get_or_create_meeting(self, session, event, season_id: int) -> Meeting:
        """Get or create meeting"""
        meeting_key = int(event['RoundNumber'])
        
        stmt = select(Meeting).where(
            Meeting.meeting_key == meeting_key,
            Meeting.seasson_id == season_id
        )
        result = await session.execute(stmt)
        meeting_obj = result.scalar_one_or_none()
        
        if not meeting_obj:
            start_date = pd.to_datetime(event['EventDate']).date()
            standard_name = self.create_standard_name(event['EventName'])
            
            meeting_obj = Meeting(
                country_name=event['Country'],
                country_code=event['Country'][:3].upper() if pd.notna(event['Country']) else None,
                date_start=start_date,
                location=event['Location'] if pd.notna(event['Location']) else event['Country'],
                meeting_key=meeting_key,
                meeting_official_name=event['EventName'],
                meeting_standard_name=standard_name,
                seasson_id=season_id
            )
            session.add(meeting_obj)
            await session.flush()
        
        return meeting_obj
    
    def create_standard_name(self, official_name: str) -> str:
        """Create standard name without sponsors"""
        name = official_name.upper()
        
        sponsors = [
            'FORMULA 1', 'ARAMCO', 'GULF AIR', 'STC', 'ROLEX', 'MSC CRUISES',
            'LENOVO', 'CRYPTO.COM', 'TAG HEUER', 'PIRELLI', 'AWS', 'QATAR AIRWAYS',
            'MOËT & CHANDON', 'HEINEKEN', 'SINGAPORE AIRLINES', 'ETIHAD AIRWAYS',
            'LOUIS VUITTON', 'HEINEKEN SILVER'
        ]
        
        for sponsor in sponsors:
            name = name.replace(sponsor, '').strip()
        
        name = ' '.join(name.split())
        
        # Handle special cases
        special_cases = {
            'EMILIA': 'EMILIA-ROMAGNA GRAND PRIX',
            'SÃO PAULO': 'SAO PAULO GRAND PRIX',
            'SAO PAULO': 'SAO PAULO GRAND PRIX',
            'CIUDAD DE MÉXICO': 'MEXICAN GRAND PRIX',
            'MEXICO': 'MEXICAN GRAND PRIX',
            'ESPAÑA': 'SPANISH GRAND PRIX',
            'ÖSTERREICH': 'AUSTRIAN GRAND PRIX',
            'ITALIA': 'ITALIAN GRAND PRIX'
        }
        
        for key, value in special_cases.items():
            if key in name:
                return value
                
        return name if name else official_name.upper()
    
    async def process_event_sessions(self, session, year: int, event, meeting_id: int):
        """Process all sessions for an event"""
        round_num = int(event['RoundNumber'])
        session_identifiers = ['FP1', 'FP2', 'FP3', 'Q', 'SQ', 'S', 'R']
        
        for session_id in session_identifiers:
            try:
                f1_session = fastf1.get_session(year, round_num, session_id)
                f1_session.load()
                
                if f1_session.results.empty:
                    continue
                
                print(f"  Processing {self.session_type_mapping.get(session_id, session_id)}...")
                
                # Create session object
                session_obj = await self.get_or_create_session(session, f1_session, meeting_id, session_id)
                
                # Process all session data
                await self.process_session_data(session, f1_session, session_obj.id, session_id)
                
            except Exception as e:
                print(f"    ⚠ Could not load {session_id}: {str(e)}")
                continue
    
    async def get_or_create_session(self, session, f1_session, meeting_id: int, session_identifier: str) -> Session:
        """Get or create session"""
        session_name = self.session_type_mapping.get(session_identifier, session_identifier)
        session_key = hash(f"{meeting_id}_{session_identifier}") % 2147483647
        
        stmt = select(Session).where(
            Session.meeting_id == meeting_id,
            Session.session_type == session_identifier
        )
        result = await session.execute(stmt)
        session_obj = result.scalar_one_or_none()
        
        if not session_obj:
            session_obj = Session(
                meeting_id=meeting_id,
                session_name=session_name,
                session_type=session_identifier,
                session_key=session_key
            )
            session.add(session_obj)
            await session.flush()
        
        return session_obj
    
    async def process_session_data(self, session, f1_session, db_session_id: int, session_type: str):
        """Process all session data"""
        session_driver_objects = {}
        
        # Process each driver in the session
        for _, driver_result in f1_session.results.iterrows():
            # Get or create driver
            driver_obj = await self.get_or_create_driver(session, driver_result)
            
            # Get or create session_driver relationship
            session_driver_obj = await self.get_or_create_session_driver(session, driver_obj.id, db_session_id)
            session_driver_objects[int(driver_result['DriverNumber'])] = session_driver_obj
            
            # Create session result
            session_result_obj = await self.create_session_result(session, driver_result, session_driver_obj.id, session_type)
            
            # Insert grid position if qualifying or race
            if session_type in ['Q', 'R']:
                await self.create_start_grid(session, driver_result, session_driver_obj.id)
            
            # Insert points if race or sprint
            if session_type in ['R', 'S'] and session_result_obj:
                await self.create_points_scored(session, driver_result, session_result_obj.id)
        
        # Process laps and stints
        await self.process_lap_data(session, f1_session, session_driver_objects)
        
        # Process pit stops
        await self.process_pit_stops(session, f1_session, session_driver_objects)
    
    async def get_or_create_driver(self, session, driver_result) -> Driver:
        """Get or create driver"""
        driver_number = int(driver_result['DriverNumber']) if pd.notna(driver_result['DriverNumber']) else None
        
        if driver_number:
            stmt = select(Driver).where(Driver.driver_number == driver_number)
            result = await session.execute(stmt)
            driver_obj = result.scalar_one_or_none()
            
            if driver_obj:
                # Update existing driver info if needed
                if pd.notna(driver_result.get('FirstName')) and pd.notna(driver_result.get('LastName')):
                    full_name = f"{driver_result['FirstName']} {driver_result['LastName']}"
                    if not driver_obj.full_name:
                        driver_obj.full_name = full_name
                
                if driver_result.get('Abbreviation') and not driver_obj.name_acronym:
                    driver_obj.name_acronym = driver_result['Abbreviation']
                
                return driver_obj
        
        # Create new driver
        full_name = None
        if pd.notna(driver_result.get('FirstName')) and pd.notna(driver_result.get('LastName')):
            full_name = f"{driver_result['FirstName']} {driver_result['LastName']}"
        
        driver_obj = Driver(
            driver_number=driver_number,
            full_name=full_name,
            name_acronym=driver_result.get('Abbreviation', None)
        )
        session.add(driver_obj)
        await session.flush()
        
        return driver_obj
    
    async def get_or_create_session_driver(self, session, driver_id: int, session_id: int) -> SessionDriver:
        """Get or create session_driver relationship"""
        stmt = select(SessionDriver).where(
            SessionDriver.driver_id == driver_id,
            SessionDriver.session_id == session_id
        )
        result = await session.execute(stmt)
        session_driver_obj = result.scalar_one_or_none()
        
        if not session_driver_obj:
            session_driver_obj = SessionDriver(
                driver_id=driver_id,
                session_id=session_id
            )
            session.add(session_driver_obj)
            await session.flush()
        
        return session_driver_obj
    
    async def create_session_result(self, session, driver_result, session_driver_id: int, session_type: str) -> SessionResult:
        """Create session result"""
        # Determine status
        status = str(driver_result.get('Status', ''))
        dnf = 'DNF' in status or 'Retired' in status
        dns = 'DNS' in status or 'Did not start' in status  
        dsq = 'DSQ' in status or 'Disqualified' in status
        
        # Get race data
        laps_completed = int(driver_result.get('Laps', 0)) if pd.notna(driver_result.get('Laps')) else 0
        final_position = int(driver_result.get('Position', 0)) if pd.notna(driver_result.get('Position')) else None
        
        # Get timing data
        fastest_lap_time = None
        if 'FastestLap' in driver_result and pd.notna(driver_result['FastestLap']):
            fastest_lap_time = self.parse_lap_time(driver_result['FastestLap'])
            
        total_time = None
        if 'Time' in driver_result and pd.notna(driver_result['Time']):
            total_time = self.parse_lap_time(driver_result['Time'])
        
        session_result_obj = SessionResult(
            session_driver_id=session_driver_id,
            number_of_laps_completed=laps_completed,
            dnf=dnf,
            dns=dns,
            dsq=dsq,
            final_position=final_position,
            fastest_lap_time=fastest_lap_time,
            total_race_time=total_time,
            status=status[:50] if status else None
        )
        
        session.add(session_result_obj)
        await session.flush()
        return session_result_obj
    
    async def create_start_grid(self, session, driver_result, session_driver_id: int):
        """Create starting grid position"""
        grid_pos = driver_result.get('GridPosition')
        if pd.notna(grid_pos):
            grid_position = int(grid_pos)
            
            # Get qualifying time
            q_time = None
            for q_session in ['Q3', 'Q2', 'Q1']:
                if q_session in driver_result and pd.notna(driver_result[q_session]):
                    q_time = self.parse_lap_time(driver_result[q_session])
                    break
            
            start_grid_obj = StartGrid(
                session_driver_id=session_driver_id,
                grid_position=grid_position,
                qualy_time=q_time
            )
            session.add(start_grid_obj)
    
    async def create_points_scored(self, session, driver_result, session_result_id: int):
        """Create points scored record"""
        points = driver_result.get('Points', 0)
        position = driver_result.get('Position', None)
        
        if pd.notna(points):
            points_earned = float(points)
            final_position = int(position) if pd.notna(position) else None
            
            # Check for fastest lap point
            fastest_lap_point = False
            if 'FastestLap' in driver_result and pd.notna(driver_result['FastestLap']) and final_position:
                if final_position <= 10:
                    position_points = [25,18,15,12,10,8,6,4,2,1]
                    expected_points = position_points[final_position-1] if final_position <= 10 else 0
                    fastest_lap_point = points_earned > expected_points
            
            points_scored_obj = PointsScored(
                session_result_id=session_result_id,
                points_earned=points_earned,
                position=final_position,
                fastest_lap_point=fastest_lap_point,
                created_at=datetime.now()
            )
            session.add(points_scored_obj)
    
    async def process_lap_data(self, session, f1_session, session_driver_objects: Dict[int, SessionDriver]):
        """Process lap and stint data"""
        if not hasattr(f1_session, 'laps') or f1_session.laps.empty:
            return
        
        stint_cache = {}  # Cache to avoid duplicate stints
        
        for _, lap in f1_session.laps.iterrows():
            driver_num = int(lap['DriverNumber']) if pd.notna(lap['DriverNumber']) else None
            if not driver_num or driver_num not in session_driver_objects:
                continue
                
            session_driver_obj = session_driver_objects[driver_num]
            
            # Get or create stint
            stint_obj = await self.get_or_create_stint(session, lap, session_driver_obj.id, stint_cache)
            
            # Create lap
            await self.create_lap(session, lap, stint_obj.id)
    
    async def get_or_create_stint(self, session, lap_data, session_driver_id: int, cache: dict) -> Stint:
        """Get or create stint with caching"""
        stint_number = int(lap_data['Stint']) if pd.notna(lap_data['Stint']) else 1
        cache_key = f"{session_driver_id}_{stint_number}"
        
        if cache_key in cache:
            return cache[cache_key]
        
        stmt = select(Stint).where(
            Stint.session_driver_id == session_driver_id,
            Stint.stint_number == stint_number
        )
        result = await session.execute(stmt)
        stint_obj = result.scalar_one_or_none()
        
        if not stint_obj:
            compound = lap_data.get('Compound', None)
            tyre_life = int(lap_data['TyreLife']) if pd.notna(lap_data['TyreLife']) else None
            
            stint_obj = Stint(
                session_driver_id=session_driver_id,
                compound=compound,
                stint_number=stint_number,
                tyre_age_at_start=tyre_life
            )
            session.add(stint_obj)
            await session.flush()
        
        cache[cache_key] = stint_obj
        return stint_obj
    
    async def create_lap(self, session, lap_data, stint_id: int):
        """Create lap record"""
        lap_number = int(lap_data['LapNumber']) if pd.notna(lap_data['LapNumber']) else None
        if not lap_number:
            return
        
        lap_obj = Lap(
            stint_id=stint_id,
            lap_number=lap_number,
            duration_sector_1=self.parse_lap_time(lap_data.get('Sector1Time')),
            duration_sector_2=self.parse_lap_time(lap_data.get('Sector2Time')),
            duration_sector_3=self.parse_lap_time(lap_data.get('Sector3Time')),
            is_pit_out_lap=bool(lap_data.get('PitOutTime')) if 'PitOutTime' in lap_data else False,
            lap_duration=self.parse_lap_time(lap_data.get('LapTime'))
        )
        session.add(lap_obj)
    
    async def process_pit_stops(self, session, f1_session, session_driver_objects: Dict[int, SessionDriver]):
        """Process pit stop data"""
        try:
            pit_laps = f1_session.laps[
                (pd.notna(f1_session.laps.get('PitInTime', pd.Series()))) |
                (pd.notna(f1_session.laps.get('PitOutTime', pd.Series())))
            ]
            
            for _, pit_lap in pit_laps.iterrows():
                driver_num = int(pit_lap['DriverNumber']) if pd.notna(pit_lap['DriverNumber']) else None
                if not driver_num or driver_num not in session_driver_objects:
                    continue
                
                session_driver_obj = session_driver_objects[driver_num]
                lap_number = int(pit_lap['LapNumber']) if pd.notna(pit_lap['LapNumber']) else None
                
                # Calculate pit duration
                pit_duration = None
                if 'PitInTime' in pit_lap and 'PitOutTime' in pit_lap:
                    pit_in = pit_lap.get('PitInTime')
                    pit_out = pit_lap.get('PitOutTime')
                    if pd.notna(pit_in) and pd.notna(pit_out):
                        try:
                            duration = pit_out - pit_in
                            if hasattr(duration, 'total_seconds'):
                                pit_duration = duration.total_seconds()
                        except:
                            pass
                
                if lap_number:
                    pit_stop_obj = PitStop(
                        session_driver_id=session_driver_obj.id,
                        lap_number=lap_number,
                        pit_duration=pit_duration
                    )
                    session.add(pit_stop_obj)
                    
        except Exception as e:
            print(f"    ⚠ Could not process pit stops: {str(e)}")
    
    def parse_lap_time(self, lap_time) -> Optional[float]:
        """Parse lap time to seconds"""
        if pd.isna(lap_time):
            return None
        
        try:
            if hasattr(lap_time, 'total_seconds'):
                return lap_time.total_seconds()
            elif isinstance(lap_time, (int, float)):
                return float(lap_time)
            elif isinstance(lap_time, str):
                if ':' in lap_time:
                    parts = lap_time.split(':')
                    if len(parts) == 2:
                        minutes = float(parts[0])
                        seconds = float(parts[1])
                        return minutes * 60 + seconds
                else:
                    return float(lap_time)
        except:
            return None
        
        return None

async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def main():
    await on_startup()
    importer = F1DataImporter()
    
    # Import recent seasons
    seasons_to_import = [2025, 2024, 2023, 2022]
    
    for year in seasons_to_import:
        try:
            await importer.import_season(year)
            print(f"✓ Completed season {year}")
        except Exception as e:
            print(f"✗ Failed to import season {year}: {str(e)}")
    
    print("Import process completed!")


if __name__ == "__main__":
    asyncio.run(main())