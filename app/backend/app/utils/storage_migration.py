"""
Storage path migration utilities.
Handles renaming S3 paths when sessions are claimed by users.
"""

from typing import Optional
from database.models import Session, ConversionJob
from utils.storage.s3_storage import S3Storage
from utils.enhanced_logger import setup_enhanced_logging, log_with_context

logger = setup_enhanced_logging()


def sanitize_email_for_path(email: str) -> str:
    """
    Sanitize email address for use in file paths.
    Replaces special characters with safe alternatives.
    """
    if not email:
        return None

    # Replace @ and other special chars
    sanitized = email.replace("@", "_at_").replace("+", "_plus_").replace(".", "_")
    return sanitized


def get_storage_identifier(session: Session) -> str:
    """
    Get the identifier to use for storage paths.
    Prefers email > alias > session_key for better organization.
    """
    if not session:
        return None

    # Check if session has an associated user with email
    if session.user and session.user.email:
        return sanitize_email_for_path(session.user.email)

    # Fall back to alias, then session_key
    return session.alias if session.alias else session.session_key


def migrate_session_storage_paths(session: Session, old_alias: str, user_email: str) -> dict:
    """
    Migrate all storage paths for a session when it's claimed by a user.
    Renames S3 objects from alias-based paths to email-based paths.

    Args:
        session: The session being claimed
        old_alias: The old session alias (used in current paths)
        user_email: The user's email (to use in new paths)

    Returns:
        dict with migration stats: {
            'success': bool,
            'jobs_migrated': int,
            'objects_moved': int,
            'errors': list
        }
    """
    if not session or not old_alias or not user_email:
        return {
            "success": False,
            "error": "Missing required parameters",
            "jobs_migrated": 0,
            "objects_moved": 0,
            "errors": [],
        }

    s3_storage = S3Storage()
    new_identifier = sanitize_email_for_path(user_email)

    stats = {"success": True, "jobs_migrated": 0, "objects_moved": 0, "errors": []}

    log_with_context(
        logger,
        "info",
        "Starting storage path migration",
        session_key=session.session_key,
        old_alias=old_alias,
        new_identifier=new_identifier,
        job_count=len(session.conversion_jobs),
    )

    # Migrate each job's storage paths
    for job in session.conversion_jobs:
        try:
            # Old path: {alias}/{job_id}/...
            # New path: {email}/{job_id}/...
            old_prefix = f"{old_alias}/{job.id}/"
            new_prefix = f"{new_identifier}/{job.id}/"

            # List all objects for this job
            objects = s3_storage.list_objects(prefix=old_prefix)

            if not objects:
                log_with_context(
                    logger,
                    "debug",
                    "No objects to migrate for job",
                    job_id=job.id,
                    old_prefix=old_prefix,
                )
                continue

            # Move each object
            for obj_key in objects:
                try:
                    # Replace the old prefix with new prefix
                    new_key = obj_key.replace(old_prefix, new_prefix, 1)

                    # Copy to new location
                    s3_storage.copy_object(obj_key, new_key)

                    # Delete old location
                    s3_storage.delete_object(obj_key)

                    stats["objects_moved"] += 1

                    log_with_context(
                        logger,
                        "debug",
                        "Migrated storage object",
                        job_id=job.id,
                        old_key=obj_key,
                        new_key=new_key,
                    )

                except Exception as obj_error:
                    error_msg = f"Failed to migrate {obj_key}: {str(obj_error)}"
                    stats["errors"].append(error_msg)
                    log_with_context(logger, "error", error_msg, job_id=job.id, old_key=obj_key)

            stats["jobs_migrated"] += 1

        except Exception as job_error:
            error_msg = f"Failed to migrate job {job.id}: {str(job_error)}"
            stats["errors"].append(error_msg)
            log_with_context(logger, "error", error_msg, job_id=job.id)
            stats["success"] = False

    log_with_context(
        logger,
        "info",
        "Storage path migration completed",
        session_key=session.session_key,
        jobs_migrated=stats["jobs_migrated"],
        objects_moved=stats["objects_moved"],
        errors_count=len(stats["errors"]),
        success=stats["success"],
    )

    return stats


def migrate_session_storage_async(session_key: str, old_alias: str, user_email: str):
    """
    Asynchronously migrate storage paths in the background.
    This prevents blocking the claim operation.
    """
    import threading
    from database import get_db_session

    def do_migration():
        db = get_db_session()
        try:
            session = db.query(Session).filter_by(session_key=session_key).first()
            if session:
                migrate_session_storage_paths(session, old_alias, user_email)
        except Exception as e:
            log_with_context(
                logger,
                "error",
                f"Async storage migration failed: {str(e)}",
                session_key=session_key,
            )
        finally:
            db.close()

    thread = threading.Thread(target=do_migration, daemon=True)
    thread.start()

    log_with_context(
        logger,
        "info",
        "Started async storage path migration",
        session_key=session_key,
        old_alias=old_alias,
        new_identifier=sanitize_email_for_path(user_email),
    )
