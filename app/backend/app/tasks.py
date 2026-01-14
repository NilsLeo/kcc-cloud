"""
Simplified Celery tasks for FOSS MangaConverter - local storage only.

This module defines Celery tasks that can be executed asynchronously by worker processes.
Tasks are queued via Redis and processed independently from the main Flask application.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from celery_config import celery_app
from database.models import get_db_session, ConversionJob
from utils.enums.job_status import JobStatus
from utils.storage import storage
from utils.command_generator import generate_kcc_command
from utils.socketio_broadcast import broadcast_queue_update

# Setup simple logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name='mangaconverter.convert_comic',
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True
)
def convert_comic_task(self, job_id):
    """
    Celery task for converting manga/comic files to e-reader formats.

    Args:
        self: Celery task instance (bound via bind=True)
        job_id (str): Unique job identifier (UUID)

    Returns:
        dict: Task result with status and job_id
    """
    db = get_db_session()
    temp_dir = None

    try:
        # Get job from database
        job = db.query(ConversionJob).filter_by(id=job_id).first()

        if not job:
            raise ValueError(f"Job {job_id} not found in database")

        logger.info(f"Starting conversion for job {job_id}: {job.input_filename}")

        # Update job status to PROCESSING
        job.status = JobStatus.PROCESSING
        job.processing_at = datetime.utcnow()
        job.processing_started_at = datetime.utcnow()
        job.estimated_duration_seconds = 300  # Static 5 minutes for now
        db.commit()

        # Broadcast update
        broadcast_queue_update()

        # Get uploaded file path
        input_path = storage.get_upload_path(job_id)
        if not input_path or not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found for job {job_id}")

        # Create temporary directory for conversion
        temp_dir = tempfile.mkdtemp(prefix=f'kcc_{job_id}_')
        logger.info(f"Created temp directory: {temp_dir}")

        # Generate KCC command
        options = job.get_options_dict()
        kcc_command = generate_kcc_command(
            input_path=input_path,
            output_dir=temp_dir,
            device_profile=job.device_profile,
            options=options
        )

        logger.info(f"Running KCC command: {' '.join(kcc_command)}")

        # Run KCC conversion
        start_time = datetime.utcnow()
        process = subprocess.Popen(
            kcc_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            cwd=temp_dir
        )

        # Stream output
        for line in process.stdout:
            logger.info(f"KCC: {line.rstrip()}")

        process.wait()

        if process.returncode != 0:
            raise RuntimeError(f"KCC conversion failed with return code {process.returncode}")

        # Calculate conversion duration
        end_time = datetime.utcnow()
        job.actual_duration = int((end_time - start_time).total_seconds())

        # Find output file
        output_files = list(Path(temp_dir).glob('*'))
        output_files = [f for f in output_files if f.is_file() and not f.name.startswith('.')]

        if not output_files:
            raise FileNotFoundError("No output file produced by KCC")

        output_file = output_files[0]
        output_filename = output_file.name

        logger.info(f"Conversion complete. Output file: {output_filename}")

        # Save output to storage
        storage.save_output(str(output_file), job_id, output_filename)

        # Update job in database
        job.output_filename = output_filename
        job.output_file_size = storage.get_file_size(storage.get_output_path(job_id))
        job.status = JobStatus.COMPLETE
        job.completed_at = datetime.utcnow()

        # Calculate actual duration
        if job.processing_started_at:
            job.actual_duration = int((job.completed_at - job.processing_started_at).total_seconds())

        db.commit()

        # Broadcast update
        broadcast_queue_update()

        logger.info(f"Job {job_id} completed successfully")

        return {
            'status': 'success',
            'job_id': job_id,
            'output_filename': output_filename
        }

    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}", exc_info=True)

        # Update job status to ERRORED
        try:
            job = db.query(ConversionJob).filter_by(id=job_id).first()
            if job:
                job.status = JobStatus.ERRORED
                job.errored_at = datetime.utcnow()
                job.error_message = str(e)
                db.commit()

                # Broadcast update
                broadcast_queue_update()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")

        raise

    finally:
        db.close()

        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temp directory: {cleanup_error}")
