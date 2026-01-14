"""
Network speed testing utilities.

Measures actual download speed using speedtest-cli and caches the result
to avoid running tests too frequently (expensive operation).
"""

import subprocess
import time
import logging
from typing import Optional
import redis

logger = logging.getLogger(__name__)

# Redis client for caching speed test results
try:
    redis_client = redis.Redis(
        host='redis',
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    redis_client.ping()
except Exception as e:
    logger.error(f"[NetworkSpeed] Failed to connect to Redis: {e}")
    redis_client = None

# Cache configuration
SPEED_TEST_CACHE_KEY = "network_speed:download_mbps"
SPEED_TEST_CACHE_TTL = 3600  # Cache for 1 hour (speed tests are expensive)
DEFAULT_SPEED_MBPS = 250  # Fallback if speed test fails


def get_download_speed_mbps() -> float:
    """
    Get the current download speed in Mbps.

    Uses cached value if available (< 1 hour old).
    Otherwise runs a speed test and caches the result.

    Returns:
        float: Download speed in Mbps
    """
    # Try to get cached value
    if redis_client:
        try:
            cached_speed = redis_client.get(SPEED_TEST_CACHE_KEY)
            if cached_speed:
                speed = float(cached_speed)
                logger.info(f"[NetworkSpeed] Using cached download speed: {speed:.2f} Mbps")
                return speed
        except Exception as e:
            logger.warning(f"[NetworkSpeed] Failed to get cached speed: {e}")

    # No cached value, run speed test
    speed = run_speed_test()

    # Cache the result
    if redis_client and speed:
        try:
            redis_client.setex(SPEED_TEST_CACHE_KEY, SPEED_TEST_CACHE_TTL, str(speed))
            logger.info(f"[NetworkSpeed] Cached speed test result: {speed:.2f} Mbps (TTL: {SPEED_TEST_CACHE_TTL}s)")
        except Exception as e:
            logger.warning(f"[NetworkSpeed] Failed to cache speed: {e}")

    return speed or DEFAULT_SPEED_MBPS


def run_speed_test() -> Optional[float]:
    """
    Run a speed test using speedtest-cli.

    Returns:
        float: Download speed in Mbps, or None if failed
    """
    try:
        logger.info("[NetworkSpeed] Running speed test (this may take 10-30 seconds)...")
        start_time = time.time()

        # Run speedtest-cli with simple output format
        # --simple returns: Ping, Download, Upload
        result = subprocess.run(
            ['python3', '-m', 'speedtest', '--simple'],
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )

        if result.returncode != 0:
            logger.error(f"[NetworkSpeed] Speed test failed: {result.stderr}")
            return None

        # Parse output: "Download: XXX.XX Mbit/s"
        for line in result.stdout.strip().split('\n'):
            if line.startswith('Download:'):
                # Extract speed value
                parts = line.split()
                if len(parts) >= 2:
                    speed_str = parts[1]
                    speed_mbps = float(speed_str)

                    elapsed = time.time() - start_time
                    logger.info(f"[NetworkSpeed] Speed test completed in {elapsed:.1f}s: {speed_mbps:.2f} Mbps")
                    return speed_mbps

        logger.error(f"[NetworkSpeed] Could not parse speed test output: {result.stdout}")
        return None

    except subprocess.TimeoutExpired:
        logger.error("[NetworkSpeed] Speed test timed out after 60 seconds")
        return None
    except FileNotFoundError:
        logger.error("[NetworkSpeed] speedtest-cli not found. Install with: pip install speedtest-cli")
        return None
    except Exception as e:
        logger.error(f"[NetworkSpeed] Speed test error: {e}")
        return None


def invalidate_speed_cache():
    """
    Invalidate the cached speed test result.
    Call this to force a new speed test on next request.
    """
    if redis_client:
        try:
            redis_client.delete(SPEED_TEST_CACHE_KEY)
            logger.info("[NetworkSpeed] Speed test cache invalidated")
        except Exception as e:
            logger.warning(f"[NetworkSpeed] Failed to invalidate cache: {e}")
