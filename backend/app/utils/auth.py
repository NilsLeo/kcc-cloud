from functools import wraps

from database import ConversionJob, get_db_session, Session, User
from database.utils import create_session, get_session, update_session_usage, get_or_create_user
from flask import jsonify, request
from utils.enhanced_logger import setup_enhanced_logging

logger = setup_enhanced_logging()


def require_session_auth(f):
    """
    Require session key authentication.
    Supports both anonymous sessions and claimed sessions.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_key = request.headers.get("X-Session-Key")
        # logger.info(f"Received session key: {session_key}")

        if not session_key:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "No session key provided. Please register first.",
                    }
                ),
                401,
            )

        # Check if the session exists in the database
        db = get_db_session()
        try:
            session_obj = get_session(db, session_key)
            if not session_obj:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Invalid session key. Please register first.",
                        }
                    ),
                    401,
                )

            # Update last_used_at timestamp for polling-based abandonment detection
            update_session_usage(db, session_key)

            # Pass session info to the route handler
            kwargs['session_obj'] = session_obj
            return f(*args, **kwargs)
        finally:
            db.close()

    return decorated_function


def require_hybrid_auth(f):
    """
    Hybrid authentication decorator.
    Accepts EITHER:
    - X-Session-Key header (anonymous or claimed session)
    - X-Clerk-User-Id header (authenticated Clerk user)

    Automatically finds or creates the appropriate session.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from utils.clerk_auth import get_optional_clerk_user_id

        session_key = request.headers.get("X-Session-Key")
        clerk_user_id = get_optional_clerk_user_id()

        db = get_db_session()
        try:
            session_obj = None

            # Priority 1: Session key provided
            if session_key:
                session_obj = get_session(db, session_key)
                if not session_obj:
                    return jsonify({
                        "success": False,
                        "error": "Invalid session key."
                    }), 401

            # Priority 2: Clerk user ID provided (find their claimed session)
            elif clerk_user_id:
                # Get or create user in the users table
                user = get_or_create_user(db, clerk_user_id)

                # Find or create a session for this user
                session_obj = db.query(Session).filter_by(user_id=user.id).first()
                if not session_obj:
                    # Auto-create session for authenticated user
                    import uuid
                    from datetime import datetime
                    session_key = str(uuid.uuid4())
                    user_agent = request.headers.get('User-Agent')
                    create_session(db, session_key, user_agent=user_agent)
                    session_obj = db.query(Session).filter_by(session_key=session_key).first()
                    session_obj.user_id = user.id
                    session_obj.claimed_at = datetime.utcnow()
                    db.commit()
                    logger.info(f"Auto-created session for Clerk user {clerk_user_id}")

            else:
                # No authentication provided
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Provide either X-Session-Key or sign in."
                }), 401

            # Pass session info to the route handler
            kwargs['session_obj'] = session_obj
            kwargs['clerk_user_id'] = clerk_user_id
            return f(*args, **kwargs)

        finally:
            db.close()

    return decorated_function
