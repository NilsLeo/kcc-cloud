import os
from datetime import datetime

from utils.enums.job_status import JobStatus
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    JSON,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


def format_bytes(bytes_value):
    """Format bytes into human-readable string (e.g., '1.5 MB')"""
    if bytes_value is None:
        return None

    if bytes_value == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(bytes_value)

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    # Format with 1 decimal place for MB and above, no decimals for B and KB
    if unit_index <= 1:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


def get_file_extension(filename):
    """Extract file extension from filename (e.g., 'file.epub' -> '.epub')"""
    if not filename:
        return None
    if "." not in filename:
        return None
    return os.path.splitext(filename)[1].lower()


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id = Column(String(36), primary_key=True)  # UUID
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.QUEUED)
    input_filename = Column(String(255), nullable=False)
    output_filename = Column(String(255))
    input_file_size = Column(BigInteger, nullable=True)  # Input file size in bytes
    output_file_size = Column(BigInteger, nullable=True)  # Output file size in bytes
    page_count = Column(Integer, nullable=True)  # Number of pages/images in input file
    download_attempts = Column(Integer, default=0)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Status transition timestamps
    queued_at = Column(DateTime, nullable=True)  # When job entered QUEUED status
    uploading_at = Column(DateTime, nullable=True)  # When job entered UPLOADING status
    processing_at = Column(DateTime, nullable=True)  # When job entered PROCESSING status
    completed_at = Column(DateTime, nullable=True)  # When job entered COMPLETE status
    downloaded_at = Column(DateTime, nullable=True)  # When job entered DOWNLOADED status
    errored_at = Column(DateTime, nullable=True)  # When job entered ERRORED status
    cancelled_at = Column(DateTime, nullable=True)  # When job entered CANCELLED status
    dismissed_at = Column(DateTime, nullable=True)  # When user dismissed the job from UI

    device_profile = Column(String(50))
    actual_duration = Column(Integer, nullable=True)  # Actual conversion time in seconds
    upload_progress_bytes = Column(
        BigInteger, default=0
    )  # Real-time upload progress in bytes (0 to input_file_size)

    # Processing progress tracking (for ETA display)
    processing_started_at = Column(DateTime, nullable=True)  # When processing actually started
    estimated_duration_seconds = Column(
        Integer, nullable=True
    )  # Estimated total duration in seconds

    # Celery task tracking
    celery_task_id = Column(
        String(36), nullable=True
    )  # Celery task ID for the conversion task (revocable)

    # Atomized conversion options (previously in JSON 'options' field)
    # Boolean options
    manga_style = Column(Boolean, default=False)
    hq = Column(Boolean, default=False)
    two_panel = Column(Boolean, default=False)
    webtoon = Column(Boolean, default=False)
    no_processing = Column(Boolean, default=False)
    upscale = Column(Boolean, default=False)
    stretch = Column(Boolean, default=False)
    autolevel = Column(Boolean, default=False)
    black_borders = Column(Boolean, default=False)
    white_borders = Column(Boolean, default=False)
    force_color = Column(Boolean, default=False)
    force_png = Column(Boolean, default=False)
    mozjpeg = Column(Boolean, default=False)
    no_kepub = Column(Boolean, default=False)
    spread_shift = Column(Boolean, default=False)
    no_rotate = Column(Boolean, default=False)
    rotate_first = Column(Boolean, default=False)

    # Integer options
    target_size = Column(Integer, nullable=True)
    splitter = Column(Integer, default=0)
    cropping = Column(Integer, default=0)
    custom_width = Column(Integer, nullable=True)
    custom_height = Column(Integer, nullable=True)

    # Float options
    gamma = Column(Integer, nullable=True)  # Using Integer for compatibility, can be REAL
    cropping_power = Column(Integer, default=1)  # Using Integer for compatibility, can be REAL
    preserve_margin = Column(Integer, default=0)  # Using Integer for compatibility, can be REAL

    # Text options
    author = Column(String(255), default="KCC")
    title = Column(String(255), nullable=True)
    output_format = Column(String(50), nullable=True)

    @property
    def output_extension(self):
        """Dynamically compute output file extension from output_filename"""
        return get_file_extension(self.output_filename)

    def get_options_dict(self):
        """Get conversion options as a dictionary from atomized columns"""
        return {
            "manga_style": self.manga_style,
            "hq": self.hq,
            "two_panel": self.two_panel,
            "webtoon": self.webtoon,
            "no_processing": self.no_processing,
            "upscale": self.upscale,
            "stretch": self.stretch,
            "autolevel": self.autolevel,
            "black_borders": self.black_borders,
            "white_borders": self.white_borders,
            "force_color": self.force_color,
            "force_png": self.force_png,
            "mozjpeg": self.mozjpeg,
            "no_kepub": self.no_kepub,
            "spread_shift": self.spread_shift,
            "no_rotate": self.no_rotate,
            "rotate_first": self.rotate_first,
            "target_size": self.target_size,
            "splitter": self.splitter,
            "cropping": self.cropping,
            "custom_width": self.custom_width,
            "custom_height": self.custom_height,
            "gamma": self.gamma,
            "cropping_power": self.cropping_power,
            "preserve_margin": self.preserve_margin,
            "author": self.author,
            "title": self.title,
            "output_format": self.output_format,
        }


# SQLite database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:////data/jobs.db",
)

# Create database engine for SQLite
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False},  # Needed for SQLite with multiple threads
)

SessionLocal = sessionmaker(bind=engine)

# Create all tables (no-op for existing tables)
Base.metadata.create_all(engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Get database session for direct use (non-generator)."""
    return SessionLocal()
