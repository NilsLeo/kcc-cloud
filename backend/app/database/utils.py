from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from .models import ConversionJob, Session, User


def get_job(db: DBSession, job_id: str) -> Optional[ConversionJob]:
    """Get a job by its ID"""
    return db.query(ConversionJob).filter(ConversionJob.id == job_id).first()


def update_job_status(
    db: DBSession, job_id: str, status: str, error_message: Optional[str] = None
):
    """Update a job's status and optional error message"""
    job = get_job(db, job_id)
    if job:
        job.status = status
        if error_message:
            job.error_message = error_message
        db.commit()
        return job
    return None


def create_job(
    db: DBSession, job_id: str, input_filename: str, device_profile: str, session_key: str = None, **options
) -> ConversionJob:
    """Create a new conversion job with atomized options"""
    import datetime
    job = ConversionJob(
        id=job_id,
        status="queued",
        input_filename=input_filename,
        device_profile=device_profile,
        session_key=session_key,
        **options  # Pass through atomized option fields
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def create_session(db: DBSession, session_key: str, user_agent: str = None) -> Session:
    """Create a new session with optional user agent tracking"""
    from faker import Faker
    from utils.user_agent_parser import parse_user_agent

    _faker = Faker()

    # Generate unique alias BEFORE creating the session object
    # This avoids the SQLAlchemy event hook database query issues
    alias = None

    # Start with single names, then concatenate if needed
    name_parts = 1

    while alias is None:
        # Generate candidate alias with specified number of name parts
        if name_parts == 1:
            candidate_alias = _faker.first_name()
        else:
            # Concatenate multiple first names with hyphens
            names = [_faker.first_name() for _ in range(name_parts)]
            candidate_alias = "-".join(names)

        # Check if this alias already exists
        exists = db.query(Session).filter(Session.alias == candidate_alias).first()
        if not exists:
            alias = candidate_alias
            break

        # If we've tried 50 attempts with current name_parts, add another part
        if name_parts < 5:  # Reasonable limit to avoid extremely long names
            name_parts += 1
        else:
            # Ultimate fallback - should be extremely rare
            alias = f"{_faker.first_name()}-{session_key[:8]}"
            break

    # Parse user agent to extract browser, OS, and device info
    parsed_ua = parse_user_agent(user_agent) if user_agent else {}

    # Create session with pre-generated alias, user agent, and parsed data
    session = Session(
        session_key=session_key,
        alias=alias,
        user_agent=user_agent,
        **parsed_ua  # Unpack parsed user agent data
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: DBSession, session_key: str) -> Optional[Session]:
    """Get a session by its key"""
    return db.query(Session).filter(Session.session_key == session_key).first()


def update_session_usage(db: DBSession, session_key: str) -> None:
    """Update the last_used_at timestamp of a session"""
    session = get_session(db, session_key)
    if session:
        session.last_used_at = datetime.utcnow()
        db.commit()


def get_jobs_by_session(db: DBSession, session_key: str) -> list[ConversionJob]:
    """Get all conversion jobs associated with a session"""
    return db.query(ConversionJob).filter(ConversionJob.session_key == session_key).all()


def get_session_with_jobs(db: DBSession, session_key: str) -> Optional[Session]:
    """Get a session with all its associated conversion jobs"""
    return db.query(Session).filter(Session.session_key == session_key).first()


# User management functions

def get_or_create_user(db: DBSession, clerk_user_id: str, email: str = None, first_name: str = None, last_name: str = None) -> User:
    """Get existing user or create new one"""
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()

    if user:
        # Update last login time
        user.last_login_at = datetime.utcnow()
        # Update email/name if provided and different
        if email and user.email != email:
            user.email = email
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name
        db.commit()
        db.refresh(user)
    else:
        # Create new user
        user = User(
            clerk_user_id=clerk_user_id,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return user


def get_user_by_clerk_id(db: DBSession, clerk_user_id: str) -> Optional[User]:
    """Get user by Clerk user ID"""
    return db.query(User).filter(User.clerk_user_id == clerk_user_id).first()


def get_session_storage_identifier(session: Session) -> str:
    """
    Get the identifier to use for storage paths.

    IMPORTANT: Storage paths are standardized to use the session_key only.
    This ensures consistency between upload and download paths and avoids
    mismatches caused by aliases or user emails.
    """
    if not session:
        return None
    return session.session_key
