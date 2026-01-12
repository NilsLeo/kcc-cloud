import logging
import json
import os
from threading import Thread
from queue import Queue

import redis


class DatabaseHandler(logging.Handler):
    """
    Redis-backed log collector.

    - Buffers all log records into Redis lists keyed by job: `job:{job_id}:logs`.
    - For records without a `job_id`, logs go to `logs:general`.
    - No direct DB connections here; logs are persisted to DB only when the
      corresponding job is persisted (status change to terminal) via RedisJobStore.persist_to_db.
    """

    def __init__(self):
        super().__init__()
        self.log_queue = Queue()

        # Configure Redis connection (align with RedisJobStore)
        redis_url = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
        host = redis_url.split('://')[1].split(':')[0]

        try:
            self.redis = redis.Redis(
                host=host,
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Quick sanity check
            self.redis.ping()
        except Exception as e:
            # Fall back to no-op if Redis is unavailable
            print(f"[DatabaseHandler] Redis unavailable for log buffering: {e}")
            self.redis = None

        self.worker_thread = Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def emit(self, record):
        """Queue log record for async Redis push (non-blocking)."""
        log_data = {
            'level': record.levelname,
            'message': self.format(record),
            'source': getattr(record, 'source', 'backend'),
            'job_id': getattr(record, 'job_id', None),
            'user_id': getattr(record, 'user_id', None),
            'context': getattr(record, 'context', {})
        }
        self.log_queue.put(log_data)

    def _worker(self):
        """Background worker pushing logs to Redis lists."""
        while True:
            try:
                log_data = self.log_queue.get()
                if log_data is None:
                    break
                self._push_to_redis(log_data)
            except Exception as e:
                print(f"[DatabaseHandler] Failed to enqueue log to Redis: {e}")

    def _push_to_redis(self, log_data: dict) -> None:
        if not self.redis:
            return
        try:
            job_id = log_data.get('job_id')
            key = f"job:{job_id}:logs" if job_id else "logs:general"

            # Append in natural order (oldest→newest) using RPUSH
            self.redis.rpush(key, json.dumps(log_data, separators=(',', ':')))

            # Align TTL with job TTL if it's a job key; otherwise keep short general logs
            ttl_seconds = 86400 if job_id else 3600
            self.redis.expire(key, ttl_seconds)
        except Exception as e:
            print(f"[DatabaseHandler] Redis push failed: {e}")
