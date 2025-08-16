from dotenv import load_dotenv
load_dotenv()
from models.db import engine, Base
from models.deps import get_db
from models.models import Season, Meeting, Session, Driver, SessionDriver, Stint, Lap, PointsPerPosition, PitStop, PositionChange, SessionResult, StartGrid, PointsScored
from httpx import AsyncClient
from asyncio import gather
from sqlalchemy import select
from datetime import datetime, timedelta
from dateutil import parser
from aiolimiter import AsyncLimiter
from random import randint
import json
from sqlalchemy.orm import selectinload

YEARS = [2025, 2024, 2023]

async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

def parse_offset(offset_str):
    sign = -1 if offset_str.startswith('-') else 1
    h, m, s = map(int, offset_str.lstrip('+-').split(':'))
    return sign * timedelta(hours=h, minutes=m, seconds=s)

# API calls
API_URL = "https://api.openf1.org/v1"
RATE_LIMIT = 2  # requests por segundo
TIME_BETWEEN_RETRIES = 10  # segundos entre reintentos
RANDOM_INTERVAL = 20  # segundos aleatorios entre reintentos
MAX_RETRIES = 20  # máximo de reintentos por solicitud

limiter = AsyncLimiter(max_rate=RATE_LIMIT, time_period=1)
cache = {}

async def rate_limited_get(url: str, client: AsyncClient, cache_key: str = None):

    async with limiter:
        for attempt in range(MAX_RETRIES):
            if cache_key and cache_key in cache:
                print(f"Cache hit for {cache_key}")
                return cache[cache_key]

            if url in cache:
                print(f"Cache hit for {url}")
                return cache[url]
            try:
                print(f"GET {url} (Intento {attempt + 1})")
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                if cache_key:
                    cache[cache_key] = data
                else:
                    cache[url] = data
                return data
            except Exception as e:
                print(f"Error en {url}: {e}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = TIME_BETWEEN_RETRIES + randint(0, RANDOM_INTERVAL)
                    print(f"Reintentando en {wait_time} segundos...")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
            

async def get_meetings(year: int, client: AsyncClient):
    cache_key = f"meetings_{year}"
    return await rate_limited_get(f"{API_URL}/meetings?year={year}", client, cache_key=cache_key)

async def get_sessions(meeting_key: int, client: AsyncClient):
    cache_key = f"sessions_{meeting_key}"
    return await rate_limited_get(f"{API_URL}/sessions?meeting_key={meeting_key}",client, cache_key=cache_key)

async def get_drivers(session_key: int, client: AsyncClient):
    cache_key = f"drivers_{session_key}"
    return await rate_limited_get(f"{API_URL}/drivers?session_key={session_key}",client, cache_key=cache_key)

async def get_stints(session_key: int, client: AsyncClient):
    cache_key = f"stints_{session_key}"
    return await rate_limited_get(f"{API_URL}/stints?session_key={session_key}",client, cache_key=cache_key)

async def get_laps(session_key: int, driver_number: int, client: AsyncClient):
    cache_key = f"laps_{session_key}_{driver_number}"
    return await rate_limited_get(f"{API_URL}/laps?session_key={session_key}&driver_number={driver_number}", client, cache_key=cache_key)

async def get_pit_stops(session_key: int, client: AsyncClient):
    cache_key = f"pit_stops_{session_key}"
    return await rate_limited_get(f"{API_URL}/pit?session_key={session_key}", client, cache_key=cache_key)

async def get_positions_changes(session_key: int, client: AsyncClient):
    cache_key = f"position_changes_{session_key}"
    return await rate_limited_get(f"{API_URL}/positions?session_key={session_key}", client, cache_key=cache_key)

async def get_session_results(session_key: int, client: AsyncClient):
    cache_key = f"session_results_{session_key}"
    return await rate_limited_get(f"{API_URL}/session_result?session_key={session_key}", client, cache_key=cache_key)

async def get_start_grid(session_key: int, client: AsyncClient):
    cache_key = f"start_grid_{session_key}"
    return await rate_limited_get(f"{API_URL}/starting_grid?session_key={session_key}", client, cache_key=cache_key)

async def get_session_driver(pit_stop, db, session_id, driver_id):
    result = await db.execute(
        select(Session)
        .options(selectinload(Session.session_drivers))  # precarga relaciones si quieres
        .where(Session.session_key == int(session_id))
    )
    session = result.scalars().first()

    result = await db.execute(
        select(Driver)
        .options(selectinload(Driver.session_drivers))
        .where(Driver.driver_number == int(driver_id))
    )
    driver = result.scalars().first()

    if not session or not driver:
        return None

    result = await db.execute(
        select(SessionDriver)
        .where(
            SessionDriver.session_id == session.id,
            SessionDriver.driver_id == driver.id
        )
    )
    session_driver = result.scalars().first()

    if not session_driver:
        session_driver = SessionDriver(session=session, driver=driver)
        db.add(session_driver)
        await db.flush()

    # Desacoplar el objeto
    await db.refresh(session_driver)  # fuerza a cargar sus atributos
    return session_driver

async def main():
    await on_startup()
    client = AsyncClient()
    async with get_db() as db:
        with open("points_per_position.json", "r") as f:
            points_per_position = json.load(f)
            # Insert points_per_position into the database if needed
            for i in points_per_position:
                pp = PointsPerPosition(position=int(i["position"]), points=float(i["points"]))
                db.add(pp)

            await db.flush()

        # Add seasons and start fetching meetings
        meeting_tasks = []
        for year in YEARS:
            season = Season(year=year)
            db.add(season)
            meeting_tasks.append(get_meetings(year, client))

        await db.flush()

        meetings_responses = await gather(*meeting_tasks)

        session_tasks = []
        # Iterate through meetings and fetch sessions
        for meeting_list in meetings_responses:
            for meeting_data in meeting_list:
                result = await db.execute(select(Season).where(Season.year == int(meeting_data["year"])))
                season = result.scalars().first()

                result = await db.execute(select(Meeting).where(Meeting.meeting_key == int(meeting_data["meeting_key"])))
                if result.scalars().first() or not season:
                    continue

                date_obj = parser.parse(meeting_data["date_start"])
                date_obj = datetime.fromisoformat(date_obj.isoformat())

                time_obj = parse_offset(meeting_data["gmt_offset"])

                meeting = Meeting(
                    country_name=meeting_data["country_name"],
                    country_code=meeting_data["country_code"],
                    date_start=date_obj,
                    gmt_offset=time_obj,
                    location=meeting_data["location"],
                    meeting_key=int(meeting_data["meeting_key"]),
                    meeting_official_name=meeting_data["meeting_official_name"],
                    seasson_id=season.id
                )
                db.add(meeting)
                session_tasks.append(get_sessions(int(meeting_data["meeting_key"]), client))

        sessions_responses = await gather(*session_tasks)

        driver_tasks = []
        stint_tasks = []
        pit_stop_tasks = []
        all_sessions = []
        position_change_tasks = []
        session_results = []
        starting_grid_tasks = []

        # Iterate through sessions and fetch drivers and stints
        for session_list in sessions_responses:
            for session_data in session_list:
                result = await db.execute(select(Meeting).where(Meeting.meeting_key == int(session_data["meeting_key"])))
                meeting = result.scalars().first()

                result = await db.execute(select(Session).where(Session.session_key == int(session_data["session_key"])))
                if result.scalars().first() or not meeting:
                    continue

                if session_data["session_type"] not in ["Qualifying", "Race", "Sprint"]:
                    print(f"Skipping session {session_data['session_key']} of type {session_data['session_type']}")
                    continue

                session = Session(
                    meeting_id=meeting.id,
                    session_name=session_data["session_name"],
                    session_type=session_data["session_type"],
                    session_key=int(session_data["session_key"])
                )
                db.add(session)
                all_sessions.append(session_data)
                driver_tasks.append(get_drivers(int(session_data["session_key"]), client))
                stint_tasks.append(get_stints(int(session_data["session_key"]), client))
                pit_stop_tasks.append(get_pit_stops(int(session_data["session_key"]), client))
                position_change_tasks.append(get_positions_changes(int(session_data["session_key"]), client))
                session_results.append(get_session_results(int(session_data["session_key"]), client))

        drivers_responses = await gather(*driver_tasks)
        stints_responses = await gather(*stint_tasks)
        pit_stops_responses = await gather(*pit_stop_tasks)
        positions_changes_responses = await gather(*position_change_tasks)
        session_results_responses = await gather(*session_results)
        starting_grid_responses = await gather(*starting_grid_tasks)

        for driver_list in drivers_responses:
            for driver_data in driver_list:
                result = await db.execute(select(Driver).where(Driver.full_name == driver_data["full_name"].title()))
                if result.scalars().first():
                    continue

                driver = Driver(
                    driver_number=int(driver_data["driver_number"]),
                    full_name=driver_data["full_name"].title(),
                    name_acronym=driver_data["name_acronym"],
                    headshot_url=driver_data["headshot_url"]
                )
                db.add(driver)

        await db.flush()

        # Insert pit stops into the database
        for pit_stops in pit_stops_responses:
            for pit_stop in pit_stops:
                session_driver = await get_session_driver(pit_stop, db, pit_stop["session_key"], pit_stop["driver_number"])
                if not session_driver:
                    continue

                pit_stop_entry = PitStop(
                    session_driver=session_driver,
                    lap_number=int(pit_stop["lap_number"]) if pit_stop["lap_number"] is not None else None,
                    pit_duration=float(pit_stop["pit_duration"]) if pit_stop["pit_duration"] is not None else None
                )
                db.add(pit_stop_entry)
        await db.flush()

        # Insert position changes into the database
        for positions_changes in positions_changes_responses:
            for position_change in positions_changes:
                session_driver = await get_session_driver(position_change, db, position_change["session_key"], position_change["driver_number"])
                if not session_driver:
                    continue

                position_change_entry = PositionChange(
                    session_driver=session_driver,
                    position=int(position_change["position"]) if position_change["position"] is not None else None,
                    date_time=parser.parse(position_change["date_time"]) if position_change["date_time"] is not None else None
                )
                db.add(position_change_entry)
        
        await db.flush()

        # Insert session results into the database (if needed)
        for session_results in session_results_responses:
            for session_result in session_results:
                session_driver = await get_session_driver(session_result, db, session_result["session_key"], session_result["driver_number"])
                if not session_driver:
                    continue

                session_result_entry = SessionResult(
                    session_driver=session_driver,
                    number_of_laps_completed=int(session_result["number_of_laps"]) if session_result["number_of_laps"] is not None else None,
                    dnf =bool(session_result["dnf"]) if session_result["dnf"] is not None else False,
                    dsq =bool(session_result["dsq"]) if session_result["dsq"] is not None else False,
                    dns =bool(session_result["dns"]) if session_result["dns"] is not None else False
                )
                db.add(session_result_entry)

                await db.flush()

                session_results = await db.execute(
                    select(SessionResult).where(
                        SessionResult.session_driver_id == session_driver.id
                    )
                )

                points_to_score = await db.execute(
                    select(PointsPerPosition).where(
                        PointsPerPosition.position == int(session_result["position"]) if session_result["position"] is not None else None
                    )
                )

                # Check if there are points to score
                points_to_score_result = points_to_score.scalars().first()
                if not points_to_score_result:
                    continue

                points_scored = PointsScored(
                    session_result=session_results.scalars().first(),
                    points_per_position=points_to_score_result,
                )
                db.add(points_scored)
        await db.flush()

        # Iterating through starting grids and adding them to the database if needed
        for starting_grids in starting_grid_responses:
            for start_grid in starting_grids:
                session_driver = await get_session_driver(start_grid, db, start_grid["session_key"], start_grid["driver_number"])
                if not session_driver:
                    continue

                start_grid_entry = StartGrid(
                    session_driver=session_driver,
                    grid_position=int(start_grid["position"]) if start_grid["position"] is not None else None,
                    qualy_time=float(start_grid["lap_duration"]) if start_grid["lap_duration"] is not None else None
                )

                db.add(start_grid_entry)
        await db.flush()
            

        # Iterate through stints and add them to the database

        for stint_list in stints_responses:
            for stint_data in stint_list:
                session_driver = await get_session_driver(stint_data, db, stint_data["session_key"], stint_data["driver_number"])
                if not session_driver:
                    continue

                stint = Stint(
                    session_driver=session_driver,
                    compound=stint_data["compound"],
                    lap_start=int(stint_data["lap_start"]) if stint_data["lap_start"] is not None else None,
                    lap_end=int(stint_data["lap_end"]) if stint_data["lap_end"] is not None else None,
                    stint_number=int(stint_data["stint_number"]),
                    tyre_age_at_start=int(stint_data["tyre_age_at_start"]) if stint_data["tyre_age_at_start"] is not None else None
                )
                db.add(stint)
        lap_requests = []
        lap_context = []

        for session_list, driver_list in zip(sessions_responses, drivers_responses):
            for session_data in session_list:
                for driver_data in driver_list:
                    lap_requests.append(get_laps(int(session_data["session_key"]), int(driver_data["driver_number"]), client))
                    lap_context.append((int(session_data["session_key"]), int(driver_data["driver_number"])))

        laps_responses = await gather(*lap_requests)

        await db.flush()

        print("Inserting laps...")

        for (session_key, driver_number), laps in zip(lap_context, laps_responses):
            result = await db.execute(select(Session).where(Session.session_key == session_key))
            session = result.scalars().first()
            result = await db.execute(select(Driver).where(Driver.driver_number == driver_number))
            driver = result.scalars().first()

            if not session or not driver:
                continue

            result = await db.execute(select(SessionDriver).where(
                SessionDriver.session_id == session.id,
                SessionDriver.driver_id == driver.id
            ))
            session_driver = result.scalars().first()
            if not session_driver:
                continue

            stint = await db.execute(select(Stint).where(
                Stint.session_driver_id == session_driver.id,
            ))
            stint = stint.scalars().first()
            if not stint:
                continue

            for lap_data in laps:
                lap = Lap(
                    stint_id=stint.id,
                    lap_number=int(lap_data["lap_number"]) if lap_data["lap_number"] is not None else None,
                    duration_sector_1=float(lap_data["duration_sector_1"]) if lap_data["duration_sector_1"] is not None else None,
                    duration_sector_2=float(lap_data["duration_sector_2"]) if lap_data["duration_sector_2"] is not None else None,
                    duration_sector_3=float(lap_data["duration_sector_3"])  if lap_data["duration_sector_3"] is not None else None,
                    is_pit_out_lap=bool(lap_data["is_pit_out_lap"]) if lap_data["is_pit_out_lap"] is not None else False,
                    lap_duration=float(lap_data["lap_duration"]) if lap_data["lap_duration"] is not None else None,
                    speed_trap=float(lap_data["st_speed"]) if lap_data["st_speed"] is not None else None
                )
                db.add(lap)



        await db.commit()

    await client.aclose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())