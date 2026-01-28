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
    # Boolean options - nullable to distinguish between "not set" and "explicitly False"
    manga_style = Column(Boolean, nullable=True)
    hq = Column(Boolean, nullable=True)
    two_panel = Column(Boolean, nullable=True)
    webtoon = Column(Boolean, nullable=True)
    no_processing = Column(Boolean, nullable=True)
    upscale = Column(Boolean, nullable=True)
    stretch = Column(Boolean, nullable=True)
    autolevel = Column(Boolean, nullable=True)
    black_borders = Column(Boolean, nullable=True)
    white_borders = Column(Boolean, nullable=True)
    force_color = Column(Boolean, nullable=True)
    force_png = Column(Boolean, nullable=True)
    mozjpeg = Column(Boolean, nullable=True)
    no_kepub = Column(Boolean, nullable=True)
    spread_shift = Column(Boolean, nullable=True)
    no_rotate = Column(Boolean, nullable=True)
    rotate_first = Column(Boolean, nullable=True)

    # Integer options - nullable to distinguish between "not set" and explicit values
    target_size = Column(Integer, nullable=True)
    splitter = Column(Integer, nullable=True)
    cropping = Column(Integer, nullable=True)
    custom_width = Column(Integer, nullable=True)
    custom_height = Column(Integer, nullable=True)

    # Float options - nullable to distinguish between "not set" and explicit values
    gamma = Column(Integer, nullable=True)  # Using Integer for compatibility, can be REAL
    cropping_power = Column(Integer, nullable=True)  # Using Integer for compatibility, can be REAL
    preserve_margin = Column(Integer, nullable=True)  # Using Integer for compatibility, can be REAL

    # Text options - nullable to distinguish between "not set" and explicit values
    author = Column(String(255), nullable=True)
    title = Column(String(255), nullable=True)
    output_format = Column(String(50), nullable=True)

    @property
    def output_extension(self):
        """Dynamically compute output file extension from output_filename"""
        return get_file_extension(self.output_filename)

    def get_options_dict(self):
        """Get conversion options as a dictionary from atomized columns.

        Only returns options that are not None (were explicitly set).
        This prevents passing defaults to command generator.
        """
        options = {}

        # Only add non-None values - these were explicitly set by frontend
        if self.manga_style is not None:
            options["manga_style"] = self.manga_style
        if self.hq is not None:
            options["hq"] = self.hq
        if self.two_panel is not None:
            options["two_panel"] = self.two_panel
        if self.webtoon is not None:
            options["webtoon"] = self.webtoon
        if self.no_processing is not None:
            options["no_processing"] = self.no_processing
        if self.upscale is not None:
            options["upscale"] = self.upscale
        if self.stretch is not None:
            options["stretch"] = self.stretch
        if self.autolevel is not None:
            options["autolevel"] = self.autolevel
        if self.black_borders is not None:
            options["black_borders"] = self.black_borders
        if self.white_borders is not None:
            options["white_borders"] = self.white_borders
        if self.force_color is not None:
            options["force_color"] = self.force_color
        if self.force_png is not None:
            options["force_png"] = self.force_png
        if self.mozjpeg is not None:
            options["mozjpeg"] = self.mozjpeg
        if self.no_kepub is not None:
            options["no_kepub"] = self.no_kepub
        if self.spread_shift is not None:
            options["spread_shift"] = self.spread_shift
        if self.no_rotate is not None:
            options["no_rotate"] = self.no_rotate
        if self.rotate_first is not None:
            options["rotate_first"] = self.rotate_first
        if self.target_size is not None:
            options["target_size"] = self.target_size
        if self.splitter is not None:
            options["splitter"] = self.splitter
        if self.cropping is not None:
            options["cropping"] = self.cropping
        if self.custom_width is not None:
            options["custom_width"] = self.custom_width
        if self.custom_height is not None:
            options["custom_height"] = self.custom_height
        if self.gamma is not None:
            options["gamma"] = self.gamma
        if self.cropping_power is not None:
            options["cropping_power"] = self.cropping_power
        if self.preserve_margin is not None:
            options["preserve_margin"] = self.preserve_margin
        if self.author is not None:
            options["author"] = self.author
        if self.title is not None:
            options["title"] = self.title
        if self.output_format is not None:
            options["output_format"] = self.output_format

        return options


# SQLite database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:////data/jobs.db",
)

# Create database engine for SQLite
# If using a file-based SQLite URL, ensure the parent directory exists
try:
    if DATABASE_URL.startswith("sqlite:///") and ":memory:" not in DATABASE_URL:
        db_file = DATABASE_URL.replace("sqlite:///", "", 1)
        parent = os.path.dirname(db_file) or "."
        os.makedirs(parent, exist_ok=True)
except Exception:
    # Directory create best-effort; permission issues will be raised by engine.connect()
    pass
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
