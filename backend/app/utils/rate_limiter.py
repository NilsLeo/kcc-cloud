"""
Redis-based rate limiter for per-session request limiting.

Usage:
    @app.route("/jobs", methods=["POST"])
    @require_session_auth
    @rate_limit(max_requests=10, window_seconds=3600)
    def create_job(session_obj=None):
        pass
"""

import redis
from functools import wraps
from flask import jsonify, request
from utils.enhanced_logger import setup_enhanced_logging, log_with_context

logger = setup_enhanced_logging()

# Initialize Redis client (connects to redis service in docker-compose or Kubernetes)
# Parse Redis hostname from CELERY_BROKER_URL env var for consistency
import os
redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
redis_host = redis_url.split('://')[1].split(':')[0]  # Extract hostname from URL

try:
    redis_client = redis.Redis(
        host=redis_host,
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    # Test connection
    redis_client.ping()
    logger.info(f"[RateLimiter] Redis connection established successfully to {redis_host}")
except Exception as e:
    logger.error(f"[RateLimiter] Failed to connect to Redis at {redis_host}: {e}")
    redis_client = None


def get_user_identifier(session_obj=None):
    """
    Get unique identifier for rate limiting.
    Prioritizes authenticated user ID over session key.

    Args:
        session_obj: Session object from @require_session_auth

    Returns:
        tuple: (identifier, user_type) where user_type is 'authenticated' or 'anonymous'
    """
    # If session has a user (authenticated), use user_id for rate limiting
    # This prevents users from bypassing limits by creating multiple sessions
    if session_obj and session_obj.user_id:
        return f"user:{session_obj.user_id}", "authenticated"

    # Otherwise use session key (anonymous user)
    session_key = request.headers.get("X-Session-Key")
    return f"session:{session_key}", "anonymous"


def rate_limit(max_requests=10, window_seconds=3600, key_prefix="rate_limit"):
    """
    Rate limit decorator using Redis sliding window counter.

    This decorator tracks requests per user/session and enforces limits.
    It adds X-RateLimit-* headers to responses for client awareness.

    Args:
        max_requests (int): Maximum requests allowed in the time window
        window_seconds (int): Time window in seconds (default: 1 hour)
        key_prefix (str): Redis key prefix for namespacing

    Returns:
        Decorated function that enforces rate limiting

    Example:
        @rate_limit(max_requests=5, window_seconds=3600)  # 5 requests per hour
        def my_endpoint():
            pass
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # If Redis is unavailable, skip rate limiting (fail open)
            if redis_client is None:
                logger.warning("[RateLimiter] Redis unavailable, skipping rate limit")
                return f(*args, **kwargs)

            # Get session object from kwargs (injected by @require_session_auth)
            session_obj = kwargs.get('session_obj')

            # Get unique identifier for this user/session
            identifier, user_type = get_user_identifier(session_obj)

            # Redis key: rate_limit:endpoint_name:identifier
            rate_key = f"{key_prefix}:{f.__name__}:{identifier}"

            try:
                # Increment counter atomically
                current_count = redis_client.incr(rate_key)

                # Set expiry on first request (only if key is new)
                if current_count == 1:
                    redis_client.expire(rate_key, window_seconds)

                # Get remaining TTL for headers
                ttl = redis_client.ttl(rate_key)
                if ttl == -1:  # Key exists but has no expiry (shouldn't happen, but defensive)
                    redis_client.expire(rate_key, window_seconds)
                    ttl = window_seconds

                # Check if limit exceeded
                if current_count > max_requests:
                    log_with_context(
                        logger, 'warning', '🚫 Rate limit exceeded',
                        identifier=identifier,
                        user_type=user_type,
                        endpoint=f.__name__,
                        current_count=current_count,
                        max_requests=max_requests,
                        retry_after=ttl
                    )

                    return jsonify({
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {max_requests} requests per {window_seconds // 60} minutes. Please try again later.",
                        "retry_after_seconds": ttl,
                        "limit": max_requests,
                        "window_seconds": window_seconds
                    }), 429

                # Log first request in window for monitoring
                if current_count == 1:
                    log_with_context(
                        logger, 'info', '🔄 Rate limit window started',
                        identifier=identifier,
                        user_type=user_type,
                        endpoint=f.__name__,
                        max_requests=max_requests,
                        window_seconds=window_seconds
                    )

                # Call the actual endpoint
                response = f(*args, **kwargs)

                # Add rate limit headers to response
                # These headers help clients implement client-side rate limiting
                if hasattr(response, 'headers'):
                    response.headers['X-RateLimit-Limit'] = str(max_requests)
                    response.headers['X-RateLimit-Remaining'] = str(max(0, max_requests - current_count))
                    response.headers['X-RateLimit-Reset'] = str(ttl)
                elif isinstance(response, tuple) and len(response) >= 2:
                    # Response is (data, status_code) or (data, status_code, headers)
                    data = response[0]
                    status_code = response[1]
                    headers = response[2] if len(response) > 2 else {}
                    headers['X-RateLimit-Limit'] = str(max_requests)
                    headers['X-RateLimit-Remaining'] = str(max(0, max_requests - current_count))
                    headers['X-RateLimit-Reset'] = str(ttl)
                    response = (data, status_code, headers)

                return response

            except redis.RedisError as e:
                # If Redis fails, log error but don't block the request (fail open)
                logger.error(f"[RateLimiter] Redis error during rate limiting: {e}")
                return f(*args, **kwargs)

        return decorated_function
    return decorator


def check_rate_limit_status(session_obj=None, endpoint_name="create_job_with_upload", max_requests=10):
    """
    Helper function to check current rate limit status without incrementing.
    Useful for displaying remaining quota to users.

    Args:
        session_obj: Session object
        endpoint_name: Name of the endpoint to check
        max_requests: Maximum requests allowed

    Returns:
        dict: Status information with remaining requests and reset time
    """
    if redis_client is None:
        return {
            "available": True,
            "limit": max_requests,
            "remaining": max_requests,
            "reset_seconds": 0
        }

    try:
        identifier, _ = get_user_identifier(session_obj)
        rate_key = f"rate_limit:{endpoint_name}:{identifier}"

        current_count = redis_client.get(rate_key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)

        ttl = redis_client.ttl(rate_key)
        if ttl == -2:  # Key doesn't exist
            ttl = 0

        return {
            "available": current_count < max_requests,
            "limit": max_requests,
            "remaining": max(0, max_requests - current_count),
            "reset_seconds": ttl
        }
    except Exception as e:
        logger.error(f"[RateLimiter] Error checking rate limit status: {e}")
        return {
            "available": True,
            "limit": max_requests,
            "remaining": max_requests,
            "reset_seconds": 0
        }
