import logging
import sys
import os
from utils.db_logger import DatabaseHandler

# Global reference to database handler for reinitializing after fork
_db_handler = None


def setup_enhanced_logging():
    """Enhanced setup with both file and database logging"""
    global _db_handler

    logger = logging.getLogger("utils")

    # Clear any existing handlers to avoid duplicates in gunicorn workers
    logger.handlers.clear()

    if True:  # Always setup handlers for each worker process
        logger.setLevel(logging.INFO)

        # Original file/console handlers
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Ensure log directory exists

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # NEW: Database handler
        try:
            _db_handler = DatabaseHandler()
            _db_handler.setLevel(logging.INFO)
            logger.addHandler(_db_handler)
            print(f"[enhanced_logger] Database handler initialized successfully")
        except Exception as e:
            print(f"[enhanced_logger] Failed to setup database logging: {e}")
            import traceback
            traceback.print_exc()

    return logger


def reinitialize_db_handler():
    """Reinitialize database handler after fork (for Celery workers)"""
    global _db_handler

    logger = logging.getLogger("utils")

    # Remove old database handler if it exists
    if _db_handler:
        try:
            logger.removeHandler(_db_handler)
        except:
            pass

    # Create new database handler
    try:
        _db_handler = DatabaseHandler()
        _db_handler.setLevel(logging.INFO)
        logger.addHandler(_db_handler)
        print(f"[enhanced_logger] Database handler re-initialized after fork")
    except Exception as e:
        print(f"[enhanced_logger] Failed to re-initialize database logging after fork: {e}")
        import traceback
        traceback.print_exc()


def log_with_context(logger, level, message, job_id=None, user_id=None, **context):
    """Log with structured context"""
    # Build enhanced message with context data for console/file logs
    context_parts = []
    
    # Add job_id and user_id to context if provided
    if job_id:
        context_parts.append(f"job_id={job_id[:4]}...")  # Truncate job_id forbrevity
    if user_id:
        context_parts.append(f"user_id={user_id[:4]}...") 
    # Add other context key-value pairs
    for key, value in context.items():
        if key != 'source':  # Skip source as it's handled separately
            # Format value nicely for logging
            if isinstance(value, (dict, list)):
                import json
                formatted_value = json.dumps(value, separators=(',', ':'))
            else:
                formatted_value = str(value)
            context_parts.append(f"{key}={formatted_value}")
    
    # Create enhanced message for console/file logs
    if context_parts:
        enhanced_message = f"{message} | {' | '.join(context_parts)}\n"
    else:
        enhanced_message = message
    
    # Create log record
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, level.upper()),
        pathname="",
        lineno=0,
        msg=enhanced_message,
        args=(),
        exc_info=None
    )
    
    # Set additional attributes for database handler
    record.job_id = job_id
    record.user_id = user_id
    record.source = context.pop('source', 'backend')  # Extract source from context, default to backend
    record.context = context
    
    logger.handle(record)
