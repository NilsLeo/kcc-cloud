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
from datetime import datetime, timezone, timedelta
from pathlib import Path

from celery_config import celery_app
from database.models import get_db_session, ConversionJob
from utils.enums.job_status import JobStatus
from utils.storage import storage
from utils.command_generator import generate_kcc_command
from utils.socketio_broadcast import broadcast_queue_update
from utils.redis_job_store import RedisJobStore
from utils.generated_estimator import estimate_from_job

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
        job.processing_at = datetime.now(timezone.utc)
        job.processing_started_at = datetime.now(timezone.utc)
        db.commit()

        # Mirror basic PROCESSING state to Redis (broadcast deferred until ETA is known)
        try:
            RedisJobStore.update_job(job_id, {
                'status': JobStatus.PROCESSING.value,
                'processing_at': job.processing_at,
                'processing_started_at': job.processing_started_at,
            })
        except Exception:
            pass

        # Get uploaded file path
        input_path = storage.get_upload_path(job_id)
        if not input_path or not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found for job {job_id}")

        # Precompute page count for all supported formats
        def _compute_page_count(path: str) -> int:
            try:
                p = Path(path)
                suffix = p.suffix.lower()
                image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tif', '.tiff'}

                # PDF
                if suffix == '.pdf':
                    try:
                        try:
                            import fitz  # PyMuPDF
                            with fitz.open(path) as doc:
                                return int(doc.page_count)
                        except Exception:
                            import pymupdf  # type: ignore
                            with pymupdf.open(path) as doc:  # pragma: no cover
                                return int(doc.page_count)
                    except Exception:
                        return 0

                # EPUB
                if suffix == '.epub':
                    import zipfile
                    try:
                        with zipfile.ZipFile(path, 'r') as zf:
                            return sum(1 for n in zf.namelist() if Path(n).suffix.lower() in image_exts)
                    except Exception:
                        return 0

                # ZIP, CBZ
                if suffix in {'.zip', '.cbz'}:
                    import zipfile
                    try:
                        with zipfile.ZipFile(path, 'r') as zf:
                            return sum(1 for n in zf.namelist() if Path(n).suffix.lower() in image_exts)
                    except Exception:
                        return 0

                # RAR, CBR
                if suffix in {'.rar', '.cbr'}:
                    try:
                        import rarfile
                        with rarfile.RarFile(path, 'r') as rf:
                            return sum(1 for n in rf.namelist() if Path(n).suffix.lower() in image_exts)
                    except Exception:
                        return 0

                # 7Z, CB7
                if suffix in {'.7z', '.cb7'}:
                    try:
                        import py7zr
                        with py7zr.SevenZipFile(path, 'r') as szf:
                            return sum(1 for n in szf.getnames() if Path(n).suffix.lower() in image_exts)
                    except Exception:
                        return 0

                # Directory
                if os.path.isdir(path):
                    total = 0
                    for root, _dirs, files in os.walk(path):
                        total += sum(1 for f in files if Path(f).suffix.lower() in image_exts)
                    return total
            except Exception:
                return 0
            return 0

        # Compute page count and estimate processing time
        page_count = _compute_page_count(input_path)
        logger.info(f"Computed page_count={page_count} for job {job_id} from {input_path}")

        job.page_count = page_count

        file_size = os.path.getsize(input_path)
        job_data = {
            'page_count': page_count,
            'file_size': file_size,
            'filename': job.input_filename or job.original_filename,
            'advanced_options': job.get_options_dict()
        }
        projected_eta = estimate_from_job(job_data)
        logger.info(f"Estimated processing time: {projected_eta}s for job {job_id}")

        # Store in database
        job.estimated_duration_seconds = projected_eta
        db.commit()

        # Store in Redis for frontend - provide absolute ETA timestamp (eta_at) and projected seconds for fallback
        try:
            eta_at = (job.processing_started_at or job.processing_at or datetime.now(timezone.utc)) + timedelta(seconds=int(projected_eta or 0))
            RedisJobStore.update_job(job_id, {
                'processing_progress': {
                    'eta_at': eta_at.isoformat(),
                    'projected_eta': projected_eta,
                }
            })
            logger.info(f"Updated Redis with projected_eta={projected_eta}s for job {job_id}")
        except Exception:
            pass

        # Now broadcast update so frontend can start ticker (ETA is available)
        broadcast_queue_update()

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
        start_time = datetime.now(timezone.utc)
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
        end_time = datetime.now(timezone.utc)
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
        job.completed_at = datetime.now(timezone.utc)

        # Calculate actual duration (handle naive vs aware datetimes safely)
        try:
            start_dt = job.processing_started_at or job.processing_at
            end_dt = job.completed_at
            if start_dt and end_dt:
                if (hasattr(start_dt, 'tzinfo') and start_dt.tzinfo) and (hasattr(end_dt, 'tzinfo') and end_dt.tzinfo):
                    job.actual_duration = int((end_dt - start_dt).total_seconds())
                else:
                    # Normalize to naive before subtracting
                    job.actual_duration = int(((end_dt.replace(tzinfo=None) if hasattr(end_dt, 'replace') else end_dt) - (start_dt.replace(tzinfo=None) if hasattr(start_dt, 'replace') else start_dt)).total_seconds())
        except Exception:
            pass

        db.commit()

        # Mirror to Redis
        try:
            RedisJobStore.update_job(job_id, {
                'status': JobStatus.COMPLETE.value,
                'completed_at': job.completed_at,
                'output_filename': job.output_filename,
                'output_file_size': job.output_file_size or 0,
                'actual_duration': job.actual_duration or 0,
            })
        except Exception:
            pass

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

                # Mirror to Redis
                try:
                    RedisJobStore.update_job(job_id, {
                        'status': JobStatus.ERRORED.value,
                        'errored_at': job.errored_at,
                        'error_message': job.error_message,
                    })
                except Exception:
                    pass

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
