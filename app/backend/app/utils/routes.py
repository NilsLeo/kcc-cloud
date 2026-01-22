import logging
import os
import uuid
from datetime import datetime
from flask import request, jsonify, send_file
from werkzeug.utils import secure_filename

from database.models import ConversionJob, get_db_session
from utils.enums.job_status import JobStatus
from utils.redis_job_store import RedisJobStore
from utils.storage import storage
from tasks import convert_comic_task
from utils.socketio_broadcast import broadcast_queue_update

logger = logging.getLogger(__name__)


ALLOWED_EXTENSIONS = {
    "cbz",
    "cbr",
    "cb7",
    "cbt",
    "pdf",
    "epub",
    "zip",
    "rar",
    "7z",
    "tar",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "webp",
}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def register_routes(app):
    """Register all Flask routes."""

    @app.route("/health", methods=["GET"])
    def health_check():
        """Health check endpoint."""
        return jsonify({"status": "healthy", "service": "mangaconverter-foss"}), 200

    @app.route("/jobs", methods=["POST"])
    def create_job():
        """
        Create a new conversion job and upload file.

        Expects:
            - file: File upload
            - device_profile: Device profile name
            - Various conversion options as form data
        """
        try:
            # Check if file is present
            if "file" not in request.files:
                return jsonify({"error": "No file provided"}), 400

            file = request.files["file"]
            if file.filename == "":
                return jsonify({"error": "No file selected"}), 400

            if not allowed_file(file.filename):
                return jsonify({"error": "File type not allowed"}), 400

            # Get conversion options
            device_profile = request.form.get("device_profile", "KV")
            input_filename = secure_filename(file.filename)
            job_id = str(uuid.uuid4())

            # Create job in database
            db = get_db_session()
            try:
                job = ConversionJob(
                    id=job_id,
                    status=JobStatus.UPLOADING,
                    input_filename=input_filename,
                    device_profile=device_profile,
                    created_at=datetime.utcnow(),
                    uploading_at=datetime.utcnow(),
                    # Boolean options
                    manga_style=request.form.get("manga_style", "false").lower() == "true",
                    hq=request.form.get("hq", "false").lower() == "true",
                    two_panel=request.form.get("two_panel", "false").lower() == "true",
                    webtoon=request.form.get("webtoon", "false").lower() == "true",
                    no_processing=request.form.get("no_processing", "false").lower() == "true",
                    upscale=request.form.get("upscale", "false").lower() == "true",
                    stretch=request.form.get("stretch", "false").lower() == "true",
                    autolevel=request.form.get("autolevel", "false").lower() == "true",
                    black_borders=request.form.get("black_borders", "false").lower() == "true",
                    white_borders=request.form.get("white_borders", "false").lower() == "true",
                    force_color=request.form.get("force_color", "false").lower() == "true",
                    force_png=request.form.get("force_png", "false").lower() == "true",
                    mozjpeg=request.form.get("mozjpeg", "false").lower() == "true",
                    no_kepub=request.form.get("no_kepub", "false").lower() == "true",
                    spread_shift=request.form.get("spread_shift", "false").lower() == "true",
                    no_rotate=request.form.get("no_rotate", "false").lower() == "true",
                    rotate_first=request.form.get("rotate_first", "false").lower() == "true",
                    # Integer options
                    target_size=(
                        int(request.form.get("target_size"))
                        if request.form.get("target_size")
                        else None
                    ),
                    splitter=int(request.form.get("splitter", 0)),
                    cropping=int(request.form.get("cropping", 0)),
                    custom_width=(
                        int(request.form.get("custom_width"))
                        if request.form.get("custom_width")
                        else None
                    ),
                    custom_height=(
                        int(request.form.get("custom_height"))
                        if request.form.get("custom_height")
                        else None
                    ),
                    gamma=int(request.form.get("gamma")) if request.form.get("gamma") else None,
                    cropping_power=int(request.form.get("cropping_power", 1)),
                    preserve_margin=int(request.form.get("preserve_margin", 0)),
                    # Text options
                    author=request.form.get("author", "KCC"),
                    title=request.form.get("title", ""),
                    output_format=request.form.get("output_format", "EPUB"),
                )

                db.add(job)
                db.commit()

                # Save uploaded file to local storage
                upload_path = storage.upload_file(file, job_id, input_filename)

                # Get file size
                file_size = storage.get_file_size(upload_path)
                if file_size:
                    job.input_file_size = file_size
                    db.commit()
                # Mirror base metadata to Redis so queue updates have filename and size
                try:
                    logger.info(
                        f"[Routes] Mirror to Redis: job_id={job_id}, filename={input_filename}, file_size={file_size}"
                    )
                    RedisJobStore.update_job(
                        job_id,
                        {
                            "status": JobStatus.UPLOADING.value,
                            "input_filename": input_filename,
                            "device_profile": device_profile,
                            "file_size": file_size or 0,
                            "created_at": job.created_at,
                        },
                    )
                except Exception:
                    pass

                # Update job status to QUEUED and start conversion task
                job.status = JobStatus.QUEUED
                job.queued_at = datetime.utcnow()
                db.commit()
                # Update Redis status to QUEUED
                try:
                    logger.info(f"[Routes] Update Redis status to QUEUED for job_id={job_id}")
                    RedisJobStore.update_job(job_id, {"status": JobStatus.QUEUED.value})
                except Exception:
                    pass

                # Queue the conversion task
                task = convert_comic_task.delay(job_id)
                job.celery_task_id = task.id
                db.commit()

                # Broadcast queue update
                try:
                    broadcast_queue_update()
                except Exception as e:
                    # Don't fail the request if broadcast fails
                    print(f"Warning: Could not broadcast queue update: {e}")

                return (
                    jsonify(
                        {
                            "job_id": job_id,
                            "status": job.status.value,
                            "message": "Job created and queued successfully",
                        }
                    ),
                    201,
                )

            finally:
                db.close()

        except ValueError as e:
            logger.error(f"Validation error during job creation: {e}")
            return jsonify({"error": "Invalid input parameters"}), 400
        except IOError as e:
            logger.error(f"File operation error during job creation: {e}")
            return jsonify({"error": "Failed to process uploaded file"}), 500
        except Exception as e:
            logger.exception(f"Unexpected error during job creation: {e}")
            return jsonify({"error": "Internal server error"}), 500

    @app.route("/status/<job_id>", methods=["GET"])
    def get_job_status(job_id):
        """Get status of a conversion job."""
        db = get_db_session()
        try:
            job = db.query(ConversionJob).filter_by(id=job_id).first()

            if not job:
                return jsonify({"error": "Job not found"}), 404

            response = {
                "job_id": job.id,
                "status": job.status.value,
                "input_filename": job.input_filename,
                "output_filename": job.output_filename,
                "device_profile": job.device_profile,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                "error_message": job.error_message,
                "input_file_size": job.input_file_size,
                "output_file_size": job.output_file_size,
                "page_count": job.page_count,
            }

            if job.status == JobStatus.COMPLETE:
                response["download_url"] = storage.get_download_url(job_id)

            return jsonify(response), 200

        finally:
            db.close()

    @app.route("/download/<job_id>", methods=["GET"])
    def download_file(job_id):
        """Download converted file."""
        db = get_db_session()
        try:
            job = db.query(ConversionJob).filter_by(id=job_id).first()

            if not job:
                return jsonify({"error": "Job not found"}), 404

            if job.status != JobStatus.COMPLETE:
                return jsonify({"error": "Job not completed yet"}), 400

            # Get output file path
            output_path = storage.get_output_path(job_id)

            if not output_path or not os.path.exists(output_path):
                return jsonify({"error": "Output file not found"}), 404

            # Update download timestamp
            job.downloaded_at = datetime.utcnow()
            job.download_attempts += 1
            db.commit()

            # Send file
            return send_file(
                output_path,
                as_attachment=True,
                download_name=job.output_filename,
                mimetype="application/octet-stream",
            )

        finally:
            db.close()

    @app.route("/jobs/<job_id>/cancel", methods=["POST"])
    def cancel_job(job_id):
        """Cancel a conversion job or dismiss it if already terminal.

        - If the job is ACTIVE (UPLOADING/QUEUED/PROCESSING): cancel it.
        - If the job is TERMINAL (COMPLETE/DOWNLOADED/ERRORED/CANCELLED): mark as dismissed.
        Always emits a queue update and updates Redis (if available) so UI state stays in sync.
        """
        db = get_db_session()
        try:
            job = db.query(ConversionJob).filter_by(id=job_id).first()

            if not job:
                return jsonify({"error": "Job not found"}), 404

            # Attempt to import Redis job store for real-time queue consistency
            try:
                from utils.redis_job_store import RedisJobStore
            except Exception:
                RedisJobStore = None  # type: ignore

            now = datetime.utcnow()

            # If already in a terminal state, treat this as a dismiss action
            if job.status in [
                JobStatus.COMPLETE,
                JobStatus.DOWNLOADED,
                JobStatus.ERRORED,
                JobStatus.CANCELLED,
            ]:
                job.dismissed_at = now
                db.commit()

                # Reflect dismissal in Redis so queue broadcasts exclude it
                if RedisJobStore:
                    try:
                        RedisJobStore.update_job(job_id, {"dismissed_at": now})
                    except Exception:
                        pass

                # Broadcast queue update (best-effort)
                try:
                    broadcast_queue_update()
                except Exception as e:
                    print(f"Warning: Could not broadcast queue update: {e}")

                return (
                    jsonify(
                        {
                            "job_id": job_id,
                            "status": job.status.value,
                            "dismissed": True,
                            "message": "Job dismissed successfully",
                        }
                    ),
                    200,
                )

            # Otherwise, cancel the active job
            if job.celery_task_id:
                from celery_config import celery_app

                celery_app.control.revoke(job.celery_task_id, terminate=True)

            job.status = JobStatus.CANCELLED
            job.cancelled_at = now
            job.error_message = "Job cancelled by user"
            db.commit()

            # Update Redis for real-time queue
            if RedisJobStore:
                try:
                    RedisJobStore.update_job(
                        job_id, {"status": JobStatus.CANCELLED.value, "cancelled_at": now}
                    )
                except Exception:
                    pass

            # Broadcast queue update (best-effort)
            try:
                broadcast_queue_update()
            except Exception as e:
                print(f"Warning: Could not broadcast queue update: {e}")

            return (
                jsonify(
                    {
                        "job_id": job_id,
                        "status": job.status.value,
                        "message": "Job cancelled successfully",
                    }
                ),
                200,
            )

        finally:
            db.close()


    @app.route("/api/queue/status", methods=["GET"])
    def get_queue_status():
        """Get overall queue status - list of all jobs."""
        db = get_db_session()
        try:
            # Exclude dismissed jobs from the queue
            jobs = (
                db.query(ConversionJob)
                .filter(ConversionJob.dismissed_at.is_(None))
                .order_by(ConversionJob.created_at.desc())
                .limit(100)
                .all()
            )

            jobs_list = []
            for job in jobs:
                jobs_list.append(
                    {
                        "job_id": job.id,
                        "status": job.status.value,
                        "input_filename": job.input_filename,
                        "output_filename": job.output_filename,
                        "device_profile": job.device_profile,
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                    }
                )

            return jsonify({"jobs": jobs_list}), 200

        finally:
            db.close()

    @app.route("/downloads", methods=["GET"])
    def get_downloads():
        """
        Get all completed conversions available for download.

        Query params:
        - limit: Max number of downloads to return (default: 100, max: 500)
        - offset: Pagination offset (default: 0)
        - include_dismissed: Include dismissed jobs (default: false)
        """
        db = get_db_session()
        try:
            # Get pagination params
            limit = request.args.get("limit", 100, type=int)
            offset = request.args.get("offset", 0, type=int)
            include_dismissed = request.args.get("include_dismissed", "true").lower() == "true"

            # Validate pagination
            if limit > 500:
                limit = 500
            if offset < 0:
                offset = 0

            # Query all COMPLETE jobs
            query = db.query(ConversionJob).filter(ConversionJob.status == JobStatus.COMPLETE)

            # Optionally exclude dismissed jobs
            if not include_dismissed:
                query = query.filter(ConversionJob.dismissed_at.is_(None))

            jobs = (
                query.order_by(ConversionJob.completed_at.desc()).limit(limit).offset(offset).all()
            )

            # Get total count for pagination
            count_query = db.query(ConversionJob).filter(ConversionJob.status == JobStatus.COMPLETE)
            if not include_dismissed:
                count_query = count_query.filter(ConversionJob.dismissed_at.is_(None))

            total_count = count_query.count()

            downloads_data = []
            skipped_count = 0

            for job in jobs:
                try:
                    # Check if output file exists
                    output_path = storage.get_output_path(job.id)
                    if not output_path or not os.path.exists(output_path):
                        logger.warning(f"Skipping job {job.id}: output file not found")
                        skipped_count += 1
                        continue

                    download_data = {
                        "job_id": job.id,
                        "original_filename": job.input_filename,
                        "converted_filename": job.output_filename,
                        "device_profile": job.device_profile,
                        "input_file_size": job.input_file_size,
                        "output_file_size": job.output_file_size,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "actual_duration": job.actual_duration,
                        "download_url": storage.get_download_url(job.id),
                        "download_attempts": job.download_attempts,
                    }

                    downloads_data.append(download_data)

                except Exception as e:
                    logger.error(f"Failed to process download for job {job.id}: {e}")
                    skipped_count += 1
                    continue

            logger.info(
                f"Downloads fetched: {len(downloads_data)} of {total_count} total "
                f"({skipped_count} skipped)"
            )

            return (
                jsonify(
                    {
                        "downloads": downloads_data,
                        "total": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_more": (offset + len(downloads_data)) < total_count,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ),
                200,
            )

        except Exception as e:
            logger.error(f"Error fetching downloads: {e}")
            return jsonify({"error": "Failed to fetch downloads"}), 500
        finally:
            db.close()

    @app.route("/downloads/<job_id>", methods=["DELETE"])
    def delete_download(job_id):
        """
        Delete a completed download from both database and filesystem.

        This will:
        - Remove the job record from the database
        - Delete input and output files from filesystem
        """
        db = get_db_session()
        try:
            job = db.query(ConversionJob).filter_by(id=job_id).first()

            if not job:
                return jsonify({"error": "Job not found"}), 404

            # Only allow deletion of completed jobs
            if job.status != JobStatus.COMPLETE:
                return (
                    jsonify(
                        {"error": "Can only delete completed jobs", "status": job.status.value}
                    ),
                    400,
                )

            # Delete files from filesystem
            try:
                storage.delete_job_files(job_id)
                logger.info(f"Deleted files for job {job_id}")
            except Exception as e:
                logger.warning(f"Failed to delete files for job {job_id}: {e}")
                # Continue with database deletion even if file deletion fails

            # Delete from database
            db.delete(job)
            db.commit()

            logger.info(f"Successfully deleted job {job_id} from database and filesystem")

            return jsonify({"message": "Download deleted successfully", "job_id": job_id}), 200

        except Exception as e:
            logger.error(f"Error deleting download {job_id}: {e}")
            db.rollback()
            return jsonify({"error": "Failed to delete download"}), 500
        finally:
            db.close()

    return app
