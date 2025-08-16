from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, Date, Interval, Text, DECIMAL, DateTime
)
from sqlalchemy.orm import relationship
from models.db import Base

class Season(Base):
    __tablename__ = "season"
    id = Column(Integer, primary_key=True)
    year = Column(Integer, nullable=False, unique=True)
    meetings = relationship("Meeting", back_populates="season")

class Meeting(Base):
    __tablename__ = "meeting"
    id = Column(Integer, primary_key=True)
    country_name = Column(String(100))
    country_code = Column(String(10))
    date_start = Column(Date)
    gmt_offset = Column(Interval)
    location = Column(String(100))
    meeting_key = Column(Integer)
    meeting_official_name = Column(String(200))  # Increased for long sponsor names
    meeting_standard_name = Column(String(100))
    seasson_id = Column(Integer, ForeignKey("season.id"))
    
    season = relationship("Season", back_populates="meetings")
    sessions = relationship("Session", back_populates="meeting")
    
    # Unique constraint on meeting_key + season combination
    __table_args__ = (
        {"extend_existing": True},
    )

class Session(Base):
    __tablename__ = "session"
    id = Column(Integer, primary_key=True)
    meeting_id = Column(Integer, ForeignKey("meeting.id"))
    session_name = Column(String(100))
    session_type = Column(String(50))
    session_key = Column(Integer)
    
    meeting = relationship("Meeting", back_populates="sessions")
    session_drivers = relationship("SessionDriver", back_populates="session")

class Driver(Base):
    __tablename__ = "driver"
    id = Column(Integer, primary_key=True)
    driver_number = Column(Integer, unique=True)
    full_name = Column(String(100))
    name_acronym = Column(String(10))
    headshot_url = Column(Text)
    
    session_drivers = relationship("SessionDriver", back_populates="driver")

class SessionDriver(Base):
    __tablename__ = "session_driver"
    id = Column(Integer, primary_key=True)
    driver_id = Column(Integer, ForeignKey("driver.id"))
    session_id = Column(Integer, ForeignKey("session.id"))
    
    driver = relationship("Driver", back_populates="session_drivers")
    session = relationship("Session", back_populates="session_drivers")
    stints = relationship("Stint", back_populates="session_driver")
    pit_stops = relationship("PitStop", back_populates="session_driver")
    session_results = relationship("SessionResult", back_populates="session_driver")
    start_grids = relationship("StartGrid", back_populates="session_driver")
    
    # Unique constraint to prevent duplicate driver-session pairs
    __table_args__ = (
        {"extend_existing": True},
    )

class Stint(Base):
    __tablename__ = "stint"
    id = Column(Integer, primary_key=True)
    session_driver_id = Column(Integer, ForeignKey("session_driver.id"))
    compound = Column(String(50))
    lap_start = Column(Integer, nullable=True)
    lap_end = Column(Integer, nullable=True)
    stint_number = Column(Integer)
    tyre_age_at_start = Column(Integer, nullable=True)
    
    session_driver = relationship("SessionDriver", back_populates="stints")
    laps = relationship("Lap", back_populates="stint")

class Lap(Base):
    __tablename__ = "lap"
    id = Column(Integer, primary_key=True)
    stint_id = Column(Integer, ForeignKey("stint.id"))
    lap_number = Column(Integer, nullable=False)
    duration_sector_1 = Column(Float, nullable=True)
    duration_sector_2 = Column(Float, nullable=True)
    duration_sector_3 = Column(Float, nullable=True)
    is_pit_out_lap = Column(Boolean, nullable=True)
    lap_duration = Column(Float, nullable=True)
    speed_trap = Column(Float, nullable=True)  # Keeping for now, can be NULL
    
    stint = relationship("Stint", back_populates="laps")

class PitStop(Base):
    __tablename__ = "pit_stop"
    id = Column(Integer, primary_key=True)
    session_driver_id = Column(Integer, ForeignKey("session_driver.id"))
    lap_number = Column(Integer, nullable=True)
    pit_duration = Column(Float, nullable=True)
    
    session_driver = relationship("SessionDriver", back_populates="pit_stops")

class SessionResult(Base):
    __tablename__ = "session_result"
    id = Column(Integer, primary_key=True)
    session_driver_id = Column(Integer, ForeignKey("session_driver.id"))
    number_of_laps_completed = Column(Integer, nullable=True)
    dnf = Column(Boolean, nullable=True)
    dns = Column(Boolean, nullable=True)
    dsq = Column(Boolean, nullable=True)
    
    # NEW FIELDS from our restructure
    final_position = Column(Integer, nullable=True)
    fastest_lap_time = Column(Float, nullable=True)
    fastest_lap_number = Column(Integer, nullable=True)
    total_race_time = Column(Float, nullable=True)
    gap_to_leader = Column(Float, nullable=True)
    status = Column(String(50), nullable=True)
    
    session_driver = relationship("SessionDriver", back_populates="session_results")
    points_scored = relationship("PointsScored", back_populates="session_result")

class StartGrid(Base):
    __tablename__ = "start_grid"
    id = Column(Integer, primary_key=True)
    session_driver_id = Column(Integer, ForeignKey("session_driver.id"))
    grid_position = Column(Integer, nullable=True)
    qualy_time = Column(Float, nullable=True)
    
    session_driver = relationship("SessionDriver", back_populates="start_grids")

# NEW TABLE: PointsScored (replaces the old points system)
class PointsScored(Base):
    __tablename__ = "points_scored"
    id = Column(Integer, primary_key=True)
    session_result_id = Column(Integer, ForeignKey("session_result.id"))
    points_earned = Column(DECIMAL(4,1), nullable=False, default=0)
    position = Column(Integer, nullable=True)  # Position that earned these points
    fastest_lap_point = Column(Boolean, default=False)  # Did they get the fastest lap bonus?
    created_at = Column(DateTime, nullable=True)
    
    session_result = relationship("SessionResult", back_populates="points_scored")

# REMOVED CLASSES (commented out for reference):
# class PositionChange - ELIMINATED
# class PointsPerPosition - ELIMINATED  
# class Points - REPLACED by PointsScored