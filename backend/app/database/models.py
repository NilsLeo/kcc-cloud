import os
import time
from datetime import datetime

from faker import Faker
from utils.enums.job_status import JobStatus
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    Table,
    create_engine,
    event,
    inspect,
    text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError

Base = declarative_base()
# Faker instance for generating unique session aliases
_faker = Faker()


def format_bytes(bytes_value):
    """Format bytes into human-readable string (e.g., '1.5 MB')"""
    if bytes_value is None:
        return None

    if bytes_value == 0:
        return "0 B"

    units = ['B', 'KB', 'MB', 'GB', 'TB']
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
    if '.' not in filename:
        return None
    return os.path.splitext(filename)[1].lower()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clerk_user_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255))
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # One-to-many relationship with sessions
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    session_key = Column(String(36), primary_key=True)  # UUID
    alias = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    claimed_at = Column(DateTime, nullable=True)  # When anonymous session was claimed
    user_agent = Column(String(500), nullable=True)  # Browser/client user agent (raw string)

    # Parsed User Agent fields
    browser_family = Column(String(100), nullable=True)  # e.g., 'Chrome', 'Safari', 'Firefox'
    browser_version = Column(String(50), nullable=True)   # e.g., '120.0.0'
    os_family = Column(String(100), nullable=True)        # e.g., 'Windows', 'iOS', 'Android'
    os_version = Column(String(50), nullable=True)        # e.g., '10', '13.5'
    device_family = Column(String(100), nullable=True)    # e.g., 'iPhone', 'iPad', 'PC'
    device_brand = Column(String(100), nullable=True)     # e.g., 'Apple', 'Samsung', 'Generic'
    device_model = Column(String(100), nullable=True)     # e.g., 'iPhone', 'SM-G960F'
    is_mobile = Column(Boolean, default=False)            # True if mobile device
    is_tablet = Column(Boolean, default=False)            # True if tablet device
    is_pc = Column(Boolean, default=False)                # True if PC/desktop

    # Foreign key to User (nullable for anonymous sessions)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="sessions")
    conversion_jobs = relationship("ConversionJob", back_populates="session")

    @property
    def is_anonymous(self):
        """Dynamically determine if session is anonymous"""
        return self.user_id is None


class ConversionJob(Base):
    __tablename__ = "conversion_jobs"

    id = Column(String(36), primary_key=True)  # UUID
    status = Column(
        Enum(JobStatus), nullable=False, default=JobStatus.QUEUED
    )
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
    abandoned_at = Column(DateTime, nullable=True)  # When job entered ABANDONED status
    dismissed_at = Column(DateTime, nullable=True)  # When user dismissed the job from UI

    device_profile = Column(String(50))
    projected_eta = Column(Integer, nullable=True)  # Estimated time in seconds
    actual_duration = Column(Integer, nullable=True)  # Actual conversion time in seconds
    upload_progress_bytes = Column(BigInteger, default=0)  # Real-time upload progress in bytes (0 to input_file_size)

    # Celery task tracking
    celery_task_id = Column(String(36), nullable=True)  # Celery task ID for the conversion task (revocable)

    # S3 multipart upload tracking
    s3_upload_id = Column(String(512), nullable=True)  # S3 multipart upload ID (R2 uses longer IDs than AWS)
    s3_key = Column(String(500), nullable=True)  # S3 object key for the uploaded file
    s3_parts_total = Column(Integer, nullable=True)  # Total number of parts in multipart upload
    s3_parts_completed = Column(Integer, nullable=True)  # Number of parts completed
    s3_parts_info = Column(JSON, nullable=True)  # Array of completed parts: [{'PartNumber': 1, 'ETag': '...'}]

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
    author = Column(String(255), default='KCC')
    title = Column(String(255), nullable=True)
    output_format = Column(String(50), nullable=True)

    # Foreign key to Session
    session_key = Column(String(36), ForeignKey("sessions.session_key"))
    session = relationship("Session", back_populates="conversion_jobs")

    @property
    def output_extension(self):
        """Dynamically compute output file extension from output_filename"""
        return get_file_extension(self.output_filename)

    def get_options_dict(self):
        """Get conversion options as a dictionary from atomized columns"""
        return {
            'manga_style': self.manga_style,
            'hq': self.hq,
            'two_panel': self.two_panel,
            'webtoon': self.webtoon,
            'no_processing': self.no_processing,
            'upscale': self.upscale,
            'stretch': self.stretch,
            'autolevel': self.autolevel,
            'black_borders': self.black_borders,
            'white_borders': self.white_borders,
            'force_color': self.force_color,
            'force_png': self.force_png,
            'mozjpeg': self.mozjpeg,
            'no_kepub': self.no_kepub,
            'spread_shift': self.spread_shift,
            'no_rotate': self.no_rotate,
            'rotate_first': self.rotate_first,
            'target_size': self.target_size,
            'splitter': self.splitter,
            'cropping': self.cropping,
            'custom_width': self.custom_width,
            'custom_height': self.custom_height,
            'gamma': self.gamma,
            'cropping_power': self.cropping_power,
            'preserve_margin': self.preserve_margin,
            'author': self.author,
            'title': self.title,
            'output_format': self.output_format,
        }


class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    source = Column(String(50), nullable=False)  # 'frontend', 'backend'
    
    # Core correlation fields
    job_id = Column(String(255))
    user_id = Column(String(255))
    
    # Structured context as JSON
    context = Column(JSON)


# Alias generation moved to create_license() function to avoid 
# SQLAlchemy event hook issues with nested database queries during transactions


# Construct the PostgreSQL database URL from environment variables
# Create database engine and session factory
# Load PostgreSQL database configuration from environment variables
PGPASSWORD = os.getenv("PGPASSWORD", "postgres")
PGUSER = os.getenv("PGUSER", "postgres")
PGDATABASE = os.getenv("PGDATABASE", "mangaconverter")
PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5432")

# Allow override via DATABASE_PUBLIC_URL environment variable
DATABASE_URL = os.getenv(
    "DATABASE_PUBLIC_URL",
    f"postgresql://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}",
)
# Append SSL mode if not already present
# Use sslmode=require for production (Railway), disable for local development
if "sslmode" not in DATABASE_URL:
    # Try to detect SSL support dynamically
    # Start with prefer (tries SSL, falls back to no SSL if not supported)
    DATABASE_URL += "?sslmode=prefer"
## Enable connection pre-ping to ensure stale/disconnected connections are revalidated before use
# Enhanced engine configuration for Railway PostgreSQL reliability
# Use NullPool for eventlet compatibility (no connection pooling with locks)
from sqlalchemy.pool import NullPool

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # Required for eventlet - disables connection pooling
    connect_args={
        "connect_timeout": 10,  # Reduced timeout for faster failure/retry
        "keepalives": 1,  # Enable TCP keepalives
        "keepalives_idle": 30,  # Start keepalives after 30s of inactivity
        "keepalives_interval": 10,  # Send keepalive every 10s
        "keepalives_count": 5,  # Max 5 keepalive probes before giving up
        "tcp_user_timeout": 10000,  # 10 seconds TCP timeout (milliseconds)
        # Note: Neon pooler doesn't support statement_timeout in connection options
        # Use SET statement_timeout in queries if needed instead
    },
    echo=False,  # Set to True for SQL debugging
    execution_options={
        "isolation_level": "AUTOCOMMIT"  # Avoid transaction overhead for simple queries
    }
)

def create_session_with_retry(max_retries=5, retry_delay=0.5):
    """Create a database session with retry logic for connection failures."""
    for attempt in range(max_retries):
        try:
            session = SessionLocal()
            # Test the connection with a simple query
            session.execute(text("SELECT 1"))
            session.commit()  # Ensure connection is fully established
            return session
        except (OperationalError, DisconnectionError) as e:
            # Close the failed session to clean up
            try:
                session.close()
            except:
                pass

            if attempt < max_retries - 1:
                print(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
                print(f"Retrying in {retry_delay:.2f} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 5)  # Exponential backoff capped at 5s
                continue
            else:
                print(f"All {max_retries} database connection attempts failed. Last error: {e}")
                raise
        except Exception as e:
            print(f"Unexpected database error during connection: {e}")
            try:
                session.close()
            except:
                pass
            raise

SessionLocal = sessionmaker(bind=engine)

# Create all tables (no-op for existing tables)
Base.metadata.create_all(engine)


def get_db():
    """Get database session with retry logic."""
    db = create_session_with_retry()
    try:
        yield db
    finally:
        db.close()

def get_db_session():
    """Get database session for direct use (non-generator)."""
    return create_session_with_retry()
