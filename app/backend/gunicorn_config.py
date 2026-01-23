"""
Gunicorn configuration file for mangaconverter backend.

This configuration patches psycopg2 for eventlet compatibility using psycogreen.
Without this patch, psycopg2's blocking I/O operations will hang eventlet greenlets.
"""


def post_fork(server, worker):
    """
    Called just after a worker has been forked.

    This is the correct place to patch psycopg2 for eventlet, as it must be done
    after the worker process has forked but before any database connections are made.
    """
    from psycogreen.eventlet import patch_psycopg

    patch_psycopg()

    server.log.info("psycopg2 patched for eventlet greenlet compatibility")
