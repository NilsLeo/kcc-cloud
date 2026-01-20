import logging
import sys
from typing import Any, Dict, Optional


def setup_enhanced_logging(name: Optional[str] = None, level: int = logging.INFO) -> logging.Logger:
    """
    Setup enhanced logging with context support.

    Args:
        name: Logger name (defaults to root logger)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or __name__)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)

    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **context: Any) -> None:
    """
    Log a message with additional context information.

    Args:
        logger: Logger instance to use
        level: Log level as string ('debug', 'info', 'warning', 'error', 'critical')
        message: Log message
        **context: Additional context key-value pairs to include in log
    """
    # Build context string if provided
    context_str = ""
    if context:
        context_parts = [f"{k}={v}" for k, v in context.items() if v is not None]
        if context_parts:
            context_str = f" [{', '.join(context_parts)}]"

    # Get the logging method based on level
    log_method = getattr(logger, level.lower(), logger.info)

    # Log with context
    log_method(f"{message}{context_str}")
