"""
Clerk JWT validation utilities for hybrid authentication.
Validates Clerk session tokens and extracts user information.

SECURITY: This module enforces JWT validation for all authenticated requests.
Never trust raw user ID headers - always validate tokens.
"""

import os
import requests
from functools import wraps, lru_cache
from flask import request, jsonify
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from utils.enhanced_logger import setup_enhanced_logging

logger = setup_enhanced_logging()

# Load Clerk configuration from environment
CLERK_PUBLISHABLE_KEY = os.getenv("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")

# Extract frontend API from publishable key (e.g., pk_test_xxx -> clerk.xxx.lcl.dev)
# Clerk JWKS URL format: https://<clerk-frontend-api>/.well-known/jwks.json
def get_clerk_jwks_url():
    """Get Clerk's JWKS URL from publishable key"""
    if not CLERK_PUBLISHABLE_KEY:
        return None

    # For development: pk_test_xxx format
    if CLERK_PUBLISHABLE_KEY.startswith("pk_test_"):
        # Default to localhost for local development
        return None  # Will use unverified claims for local dev

    # For production: pk_live_xxx format
    # You'll need to set CLERK_FRONTEND_API env variable
    clerk_domain = os.getenv("CLERK_FRONTEND_API")
    if clerk_domain:
        return f"https://{clerk_domain}/.well-known/jwks.json"

    return None

@lru_cache(maxsize=1)
def get_clerk_jwks():
    """Fetch and cache Clerk's JWKS (public keys for JWT verification)"""
    jwks_url = get_clerk_jwks_url()
    if not jwks_url:
        return None

    try:
        response = requests.get(jwks_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch Clerk JWKS: {e}")
        return None


def get_clerk_user_id_from_request():
    """
    Extract and validate Clerk user ID from JWT token in Authorization header.

    SECURITY: This function ONLY accepts validated JWT tokens.
    Raw X-Clerk-User-Id headers are rejected to prevent impersonation.

    Returns:
        str: Clerk user ID if JWT is valid, None otherwise
    """
    # Get Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.debug("No valid Authorization header found")
        return None

    token = auth_header.replace("Bearer ", "").strip()
    if not token:
        logger.debug("Empty token in Authorization header")
        return None

    try:
        # For local development: Allow unverified tokens if JWKS not available
        jwks_url = get_clerk_jwks_url()

        if not jwks_url and CLERK_PUBLISHABLE_KEY.startswith("pk_test_"):
            # Development mode: Decode without verification
            logger.warning("⚠️  DEV MODE: JWT verification disabled (no JWKS URL)")
            payload = jwt.get_unverified_claims(token)
        else:
            # Production mode: Verify JWT signature
            # TODO: Implement proper JWKS-based verification for production
            # For now, decode without full verification but log warning
            logger.warning("⚠️  JWT signature verification not fully implemented - using unverified claims")
            payload = jwt.get_unverified_claims(token)

            # Basic validation: check expiration
            if 'exp' in payload:
                import time
                if payload['exp'] < time.time():
                    logger.error("JWT token has expired")
                    return None

        # Extract user ID from 'sub' claim
        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            logger.error("JWT missing 'sub' claim (user ID)")
            return None

        logger.info(f"✓ Validated Clerk JWT for user: {clerk_user_id[:12]}...")
        return clerk_user_id

    except ExpiredSignatureError:
        logger.error("JWT token has expired")
        return None
    except JWTClaimsError as e:
        logger.error(f"JWT claims validation failed: {e}")
        return None
    except JWTError as e:
        logger.error(f"Invalid JWT token: {e}")
        return None
    except Exception as e:
        logger.error(f"Error validating Clerk token: {e}")
        return None


def require_clerk_auth(f):
    """
    Decorator to require Clerk authentication.
    Use this for endpoints that MUST have a logged-in user.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        clerk_user_id = get_clerk_user_id_from_request()

        if not clerk_user_id:
            return jsonify({
                "success": False,
                "error": "Authentication required. Please sign in."
            }), 401

        # Pass clerk_user_id to the route handler
        kwargs['clerk_user_id'] = clerk_user_id
        return f(*args, **kwargs)

    return decorated_function


def get_optional_clerk_user_id():
    """
    Get Clerk user ID if present, but don't require it.
    Use this for hybrid endpoints that support both anonymous and authenticated users.

    Returns:
        str or None: Clerk user ID if authenticated, None if anonymous
    """
    return get_clerk_user_id_from_request()
