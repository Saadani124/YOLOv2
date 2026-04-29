from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from typing import Optional

from config import DATABASE_URL

# Create database engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    pool_size=20,        # Base pool size (default was 5)
    max_overflow=30,     # Extra connections beyond pool_size (default was 10)
    pool_timeout=10,     # Seconds to wait for a connection before erroring
    echo=False           # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(36), unique=True, index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer)  # Size in bytes
    duration = Column(Float)  # Duration in seconds
    language = Column(String(10))
    full_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    segments = relationship("Segment", back_populates="video", cascade="all, delete-orphan")
    detections = relationship("ObjectDetection", back_populates="video", cascade="all, delete-orphan")
    visual_texts = relationship("VisualText", back_populates="video", cascade="all, delete-orphan")
    search_history = relationship("SearchHistory", back_populates="video", cascade="all, delete-orphan")




class Segment(Base):
    __tablename__ = "segments"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(36), ForeignKey("videos.video_id"), nullable=False, index=True)
    segment_id = Column(Integer, nullable=False)
    start_time = Column(Float, nullable=False, index=True)
    end_time = Column(Float, nullable=False)
    text = Column(Text, nullable=False)
    confidence = Column(Float)  # Transcription confidence score
    
    # Relationships
    video = relationship("Video", back_populates="segments")
    words = relationship("Word", back_populates="segment", cascade="all, delete-orphan")


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    segment_id = Column(Integer, ForeignKey("segments.id"), nullable=False, index=True)
    word = Column(String(255), nullable=False, index=True)
    start_time = Column(Float, nullable=False, index=True)
    end_time = Column(Float, nullable=False)
    confidence = Column(Float)
    
    # Relationships
    segment = relationship("Segment", back_populates="words")


class ObjectDetection(Base):
    __tablename__ = "object_detections"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(36), ForeignKey("videos.video_id"), nullable=False, index=True)
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False, index=True)  # Time in seconds
    object_class = Column(String(100), nullable=False, index=True)  # e.g., "car", "person"
    confidence = Column(Float, nullable=False)  # Detection confidence (0.0-1.0)
    bbox_x = Column(Float)  # Bounding box X coordinate
    bbox_y = Column(Float)  # Bounding box Y coordinate
    bbox_width = Column(Float)  # Bounding box width
    bbox_height = Column(Float)  # Bounding box height
    
    # Relationships
    video = relationship("Video", back_populates="detections")


class VisualText(Base):
    """Text detected in video frames via OCR"""
    __tablename__ = "visual_texts"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(36), ForeignKey("videos.video_id"), nullable=False, index=True)
    frame_number = Column(Integer, nullable=False)
    timestamp = Column(Float, nullable=False, index=True)  # Time in seconds
    text = Column(String(512), nullable=False, index=True)  # The detected text
    confidence = Column(Float, nullable=False)  # OCR confidence (0.0-1.0)
    bbox_x = Column(Float)
    bbox_y = Column(Float)
    bbox_width = Column(Float)
    bbox_height = Column(Float)
    
    # Relationships
    video = relationship("Video", back_populates="visual_texts")


class SearchHistory(Base):
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(36), ForeignKey("videos.video_id"), nullable=False, index=True)
    query = Column(String(512), nullable=False, index=True)
    result_count = Column(Integer, default=0)
    clicked_result = Column(Boolean, default=False)
    search_type = Column(String(20), default="transcript")  # "transcript" or "object"
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    video = relationship("Video", back_populates="search_history")


def get_db():

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():

    return SessionLocal()


def init_db():

    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully!")


def drop_all_tables():

    print("⚠️  Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    print("✓ All tables dropped!")


def reset_db():

    drop_all_tables()
    init_db()