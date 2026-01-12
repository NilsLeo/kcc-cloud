import datetime
import json
import os
import shutil
import subprocess
import uuid
from typing import Any, Dict, List, Optional, Tuple

import subprocess
from typing import List, Optional

from database import ConversionJob, get_db_session
from utils.enums.job_status import JobStatus
from utils.command_generator import generate_command
from utils.file_processors import process_7z, process_rar, process_zip, unwrap_nested_archives
from utils.globals import KCC_PATH, UPLOADS_DIRECTORY
from utils.enhanced_logger import setup_enhanced_logging, log_with_context
from utils.eta_estimator import estimate_eta
from utils.job_status import change_status
from utils.storage.s3_storage import S3Storage

# Initialize logging
logger = setup_enhanced_logging()


def get_file_info(input_path: str) -> Tuple[str, str, str]:
    log_with_context(
        logger, 'info', f'Getting info for filepath: {input_path}',
        file_path=input_path,
        source='worker'
    )
    """Extract base name, extension, and safe filename from a path."""
    base_name = os.path.basename(input_path)
    name, ext = os.path.splitext(base_name)
    safe_name = name.replace(" ", "_")
    return name, ext, safe_name


def find_file_by_extensions(
    directory: str,
    extensions: List[str],
    base_name: Optional[str] = None,
    newest: bool = False,
) -> Optional[str]:
    """Find a file with given extensions, optionally filtering by base name and/or getting newest."""
    matching_files = []
    for ext in extensions:
        if base_name:
            potential_file = os.path.join(directory, base_name + ext)
            if os.path.exists(potential_file):
                matching_files.append(os.path.basename(potential_file))
        else:
            matching_files.extend([f for f in os.listdir(directory) if f.endswith(ext)])

    if not matching_files:
        return None

    if newest:
        matching_files.sort(
            key=lambda x: os.path.getctime(os.path.join(directory, x)), reverse=True
        )

    return os.path.join(directory, matching_files[0])


def extract_archive(input_path: str, target_dir: str, job_id: str = None, user_id: str = None) -> str:
    """
    Extract archive files (zip, rar, cbz, cbr, 7z, cb7) to the specified directory.
    Automatically unwraps nested archives if the archive contains only another archive.
    """
    file_ext = os.path.splitext(input_path)[1].lower()

    try:
        # Choose the appropriate processing method based on file extension
        processors = {
            ".zip": process_zip,
            ".cbz": process_zip,
            ".rar": process_rar,
            ".cbr": process_rar,
            ".7z": process_7z,
            ".cb7": process_7z,
        }

        processor = processors.get(file_ext)
        if not processor:
            raise Exception(f"Unsupported file extension: {file_ext}")

        # Extract the archive
        extracted_dir = processor(input_path, target_dir, job_id=job_id, user_id=user_id)

        # Unwrap nested archives (if archive contains only another archive, extract it recursively)
        final_dir = unwrap_nested_archives(extracted_dir, job_id=job_id, user_id=user_id)

        return final_dir
    except Exception as e:
        shutil.rmtree(target_dir)
        raise Exception(f"Failed to extract archive: {str(e)}")


def run_command(command: List[str]) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    result = subprocess.run(command, capture_output=True, text=True)

    # Only log errors, not routine command output
    if result.stderr:
        log_with_context(
            logger, 'error', f'Command error: {result.stderr}',
            command=command,
            command_error=result.stderr,
            source='worker'
        )

    return result


def convert_file(command: List[str], job_id: Optional[str] = None, user_id: Optional[str] = None) -> subprocess.CompletedProcess:
    """Execute the conversion command and log the result."""

    # Log the command being run
    log_with_context(
        logger, 'info', f'Running command: {" ".join(command)}',
        job_id=job_id,
        user_id=user_id,
        source='worker'
    )

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        # Parse page count from KCC output
        page_count = None
        if result.stdout and result.stdout.strip():
            # Split output into lines and log each significant line
            output_lines = result.stdout.strip().split('\n')
            for line in output_lines:
                line = line.strip()
                # Extract page count if present
                if line.startswith('PAGECOUNT:'):
                    try:
                        page_count = int(line.split(':')[1].strip())
                        log_with_context(
                            logger, 'info', f'Extracted page count: {page_count}',
                            job_id=job_id,
                            user_id=user_id,
                            page_count=page_count,
                            source='worker'
                        )
                    except (ValueError, IndexError) as e:
                        log_with_context(
                            logger, 'warning', f'Failed to parse page count from line: {line}',
                            job_id=job_id,
                            user_id=user_id,
                            error=str(e),
                            source='worker'
                        )
                if line and not line.startswith('comic2ebook v'):  # Skip version line
                    log_with_context(
                        logger, 'info', f'KCC: {line}',
                        job_id=job_id,
                        user_id=user_id,
                        source='worker'
                    )

        # Add page_count as custom attribute to result object
        result.page_count = page_count

        # Log final result
        if result.returncode == 0:
            log_with_context(
                logger, 'info', 'Command completed successfully',
                job_id=job_id,
                user_id=user_id,
                source='worker'
            )
        else:
            log_with_context(
                logger, 'error', f'Command failed (exit code {result.returncode})',
                job_id=job_id,
                user_id=user_id,
                stderr=result.stderr.strip() if result.stderr else None,
                source='worker'
            )

        return result

    except subprocess.SubprocessError as e:
        log_with_context(
            logger, 'error', f'Subprocess error during conversion: {str(e)}',
            job_id=job_id,
            user_id=user_id,
            error_type=type(e).__name__,
            source='worker'
        )
        raise

    except Exception as e:
        log_with_context(
            logger, 'error', f'Unexpected error during conversion: {str(e)}',
            job_id=job_id,
            user_id=user_id,
            error_type=type(e).__name__,
            source='worker'
        )
        raise


def process_file(job_id: str, filename: str, options: Dict[str, Any]) -> str:
    """Process a file with the given options and return the output file path."""
    filename_without_ext = get_filename_without_extension(filename)
    input_path = os.path.join(UPLOADS_DIRECTORY, f"{job_id}/input/{filename}")
    
    # Get context for structured logging
    session_key = options.get("session_key", "")  # Get session key for tracking
    device_profile = options.get("device_profile")  # Get device profile from options
    
    log_with_context(
        logger, 'info', f'Processing file: {input_path}',
        job_id=job_id,
        user_id=session_key,
        filename=filename,
        file_path=input_path,
        source='worker'
    )
    
    # Check file size before processing
    max_file_size = 1024 * 1024 * 1024  # 1GB
    if os.path.getsize(input_path) > max_file_size:
        raise Exception("File too large")
    
    # Validate and determine file type
    from utils.file_validation import validate_file_extension, UnsupportedFileFormatError, SUPPORTED_FORMATS

    filename = os.path.basename(input_path)
    try:
        validate_file_extension(filename)
    except UnsupportedFileFormatError as e:
        log_with_context(
            logger, 'error', f'File validation failed: {e.message}',
            job_id=job_id,
            user_id=session_key,
            filename=filename,
            source='worker'
        )
        raise

    file_ext = os.path.splitext(input_path)[1].lower()

    # Files that KCC can handle directly (PDF, EPUB)
    if file_ext in SUPPORTED_FORMATS['direct']:
        log_with_context(
            logger, 'info', f'Processing {file_ext} file directly - no extraction needed',
            job_id=job_id,
            user_id=session_key,
            file_type=file_ext,
            source='worker'
        )
        # KCC can handle these files directly
        conversion_input_path = input_path
    # Archive files that need extraction (ZIP, RAR, 7Z, etc.)
    elif file_ext in SUPPORTED_FORMATS['archive']:
        try:
            log_with_context(
                logger, 'info', f'Extracting {file_ext} archive before conversion',
                job_id=job_id,
                user_id=session_key,
                file_type=file_ext,
                source='worker'
            )
            extracted_path = os.path.join(UPLOADS_DIRECTORY, job_id)
            final_extracted_path = extract_archive(input_path, extracted_path, job_id, session_key)
            # Use the final unwrapped folder as input (handles nested archives)
            conversion_input_path = final_extracted_path
        except Exception as e:
            log_with_context(
                logger, 'error', f'Archive extraction failed: {str(e)}',
                job_id=job_id,
                user_id=session_key,
                error_type=type(e).__name__,
                source='worker'
            )
            raise
    else:
        # This should not happen due to earlier validation, but keep as safety check
        raise UnsupportedFileFormatError(filename, file_ext)

    # Log the device profile and input path
    log_with_context(
        logger, 'info', f'Using device profile: {device_profile}',
        job_id=job_id,
        user_id=session_key,
        device_profile=device_profile,
        source='worker'
    )
    log_with_context(
        logger, 'info', f'Input path for conversion: {conversion_input_path}',
        job_id=job_id,
        user_id=session_key,
        input_path=conversion_input_path,
        source='worker'
    )

    output_dir = os.path.join(UPLOADS_DIRECTORY, job_id, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    command_options = {
        "input_path": conversion_input_path,
        "output_dir": output_dir,
        "device_profile": device_profile,
        "kcc_path": options.get("kcc_path", ""),
        "advanced_options": {
            **options.get("advanced_options", {}),
        },
    }

    # Generate command with the updated options
    command = generate_command(command_options, job_id, session_key)

    # Run conversion
    result = convert_file(command, job_id, session_key)

    # Extract page count from result
    page_count = getattr(result, 'page_count', None)

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        log_with_context(
            logger, 'error', 'Conversion failed',
            job_id=job_id,
            user_id=session_key,
            return_code=result.returncode,
            error_message=error_msg,
            source='worker'
        )
        raise Exception(f"Conversion failed: {error_msg}")
    else:
        # Find the output file in the output directory
        output_files = os.listdir(output_dir)
        if not output_files:
            raise Exception("No output file found after conversion")

        output_file_path = os.path.join(output_dir, output_files[0])

        # Return both the output file path and page count
        return output_file_path, page_count


def get_filename_without_extension(filepath: str) -> str:
    """Return the filename without its extension from a given file path."""
    base_name = os.path.basename(filepath)  # Extract the base name
    name, _ = os.path.splitext(base_name)  # Split the name and extension
    return name


# Removed job cancellation checking - no longer needed


def process_conversion(
    job_id, upload_name, session_key, options, device_profile, alias
):
    db = get_db_session()
    start_time = datetime.datetime.now()
    
    try:
        # Prepare conversion options
        advanced_options = options.get("advanced_options", {})
        conversion_options = {
            "session_key": session_key,
            "job_id": job_id,
            "device_profile": device_profile,
            "advanced_options": advanced_options,
            "kcc_path": KCC_PATH,
        }

        # Get input file size from S3
        s3_storage = S3Storage()
        input_key = f"{alias}/{job_id}/input/{upload_name}"
        input_file_size = s3_storage.get_object_size(input_key)

        # Calculate ETA estimate
        file_extension = os.path.splitext(upload_name)[1]

        # Get system resources
        import psutil
        cpu_count = psutil.cpu_count() or 3
        available_memory_gb = 2.0  # Backend container limit


        # Update existing job record with ETA and file info
        try:
            job = db.query(ConversionJob).get(job_id)

            # Calculate estimated ETA (needed for both new and existing jobs)
            # For new jobs, create a temporary job object for ETA estimation
            if job:
                job.input_file_size = input_file_size
                estimated_eta = estimate_eta(job)
                # Cap ETA at 5 minutes (300 seconds)
                try:
                    if estimated_eta is not None:
                        estimated_eta = max(1, min(float(estimated_eta), 300.0))
                except Exception:
                    estimated_eta = 300.0
            else:
                # Create temporary job for ETA estimation
                temp_job = ConversionJob(
                    id=job_id,
                    input_filename='',  # Required field
                    input_file_size=input_file_size,
                    device_profile=device_profile,
                    # Set boolean options from the options dict
                    upscale=options.get('upscale', False),
                    autolevel=options.get('autolevel', False),
                    manga_style=options.get('manga_style', False),
                    hq=options.get('hq', False),
                    two_panel=options.get('two_panel', False),
                    webtoon=options.get('webtoon', False),
                )
                estimated_eta = estimate_eta(temp_job)
                # Cap ETA at 5 minutes (300 seconds)
                try:
                    if estimated_eta is not None:
                        estimated_eta = max(1, min(float(estimated_eta), 300.0))
                except Exception:
                    estimated_eta = 300.0

            if job:
                # No cancellation checks - process all jobs

        # Enhanced structured logging
                log_with_context(
                    logger, 'info', 'Conversion started',
                    job_id=job_id,
                    user_id=session_key,
                    filename=upload_name,
                    device_profile=device_profile,
                    file_size=input_file_size,
                    projected_eta=estimated_eta,
                    projected_eta_minutes=round(estimated_eta / 60, 1),
                    source='worker'
                )
                job.projected_eta = estimated_eta
                # Worker broadcasts PROCESSING status with ETA data (event listener only updates DB)
                change_status(job, JobStatus.PROCESSING, db, session_key, {
                    'projected_eta': estimated_eta,
                    'estimated_eta_minutes': round(estimated_eta / 60, 1)
                }, broadcast=True)
                # Don't reset upload_progress_bytes - it tracks input upload which is already done
                db.commit()
                
            else:
                # Fallback: create job if it doesn't exist (shouldn't happen)
                log_with_context(
                    logger, 'warning', 'Job not found, creating new job record',
                    job_id=job_id,
                    user_id=session_key,
                    source='worker'
                )
                new_job = ConversionJob(
                    id=job_id,
                    status=JobStatus.PROCESSING,
                    input_filename=upload_name,
                    input_file_size=input_file_size,
                    device_profile=device_profile,
                    session_key=session_key,
                    projected_eta=estimated_eta,
                    upload_progress_bytes=input_file_size,  # Upload complete
                    processing_at=datetime.datetime.utcnow(),  # Set timestamp for PROCESSING status
                    # Set boolean options from the options dict
                    upscale=options.get('upscale', False),
                    autolevel=options.get('autolevel', False),
                    manga_style=options.get('manga_style', False),
                    hq=options.get('hq', False),
                    two_panel=options.get('two_panel', False),
                    webtoon=options.get('webtoon', False),
                    no_processing=options.get('no_processing', False),
                    stretch=options.get('stretch', False),
                    black_borders=options.get('black_borders', False),
                    white_borders=options.get('white_borders', False),
                    force_color=options.get('force_color', False),
                    force_png=options.get('force_png', False),
                    mozjpeg=options.get('mozjpeg', False),
                )
                db.add(new_job)
                db.commit()
                job = new_job
        except Exception as db_error:
            db.rollback()
            log_with_context(
                logger, 'error', f'Failed to update job record: {db_error}',
                job_id=job_id,
                user_id=session_key,
                error_type=type(db_error).__name__,
                source='worker'
            )
            raise  # Re-raise the exception to be handled by caller

        log_with_context(
            logger, 'info', 'File processing started',
            job_id=job_id,
            user_id=session_key,
            status='processing',
            upload_progress_bytes=input_file_size,
            source='worker'
        )

        # Download file from S3 to local filesystem (for multipart uploads)
        local_dir = os.path.join(UPLOADS_DIRECTORY, job_id, "input")
        os.makedirs(local_dir, exist_ok=True)
        local_file_path = os.path.join(local_dir, upload_name)

        # Check if file exists locally (from direct upload) or needs to be downloaded from S3
        if not os.path.exists(local_file_path):
            log_with_context(
                logger, 'info', 'Downloading file from S3',
                job_id=job_id,
                user_id=session_key,
                s3_key=input_key,
                local_path=local_file_path,
                source='worker'
            )
            s3_storage.client.download_file(
                s3_storage.bucket,
                input_key,
                local_file_path
            )
            log_with_context(
                logger, 'info', 'File downloaded from S3 successfully',
                job_id=job_id,
                user_id=session_key,
                s3_key=input_key,
                local_path=local_file_path,
                file_size=os.path.getsize(local_file_path),
                source='worker'
            )
        else:
            log_with_context(
                logger, 'info', 'File already exists locally, skipping S3 download',
                job_id=job_id,
                user_id=session_key,
                local_path=local_file_path,
                source='worker'
            )

        # No cancellation checks - process all jobs

        output_file, page_count = process_file(job_id, upload_name, conversion_options)
        output_file_name = os.path.basename(output_file)
        filename = os.path.basename(output_file)

        # Log page count if available
        if page_count is not None:
            log_with_context(
                logger, 'info', f'Input file page count: {page_count}',
                job_id=job_id,
                user_id=session_key,
                page_count=page_count,
                source='worker'
            )

        minio_output_path = f"{alias}/{job_id}/output/{output_file_name}"

        # No cancellation checks - process all jobs

        # Keep status as PROCESSING during output upload - UPLOADING is only for input upload
        log_with_context(
            logger, 'info', 'Starting output file upload to S3 (status remains PROCESSING)',
            job_id=job_id,
            user_id=session_key,
            status='processing',
            source='worker'
        )

        log_with_context(
            logger, 'info', 'Starting S3 upload',
            job_id=job_id,
            user_id=session_key,
            output_path=minio_output_path,
            status='uploading',
            source='worker'
        )

        # Get file size for progress calculation
        file_size = os.path.getsize(output_file)

        # Log upload start
        log_with_context(
            logger, 'info', f'Starting upload to S3: {minio_output_path}',
            job_id=job_id,
            user_id=session_key,
            output_path=minio_output_path,
            file_size=file_size,
            source='worker'
        )
        
        # Upload output file to S3 (no progress tracking needed for output upload)
        s3_storage.upload(output_file, minio_output_path)

        # Log upload completion
        log_with_context(
            logger, 'info', f'Output file upload completed: {minio_output_path}',
            job_id=job_id,
            user_id=session_key,
            output_path=minio_output_path,
            source='worker'
        )

        # Get output file size from S3 after upload
        output_file_size = s3_storage.get_object_size(minio_output_path)
        processing_time = (datetime.datetime.now() - start_time).total_seconds()
        actual_duration = int(processing_time)

        key = minio_output_path
        presigned_url = s3_storage.presigned_url(key)

        job = db.query(ConversionJob).get(job_id)
        if job:
            job.output_filename = filename
            job.output_file_size = output_file_size
            job.page_count = page_count  # Save page count to database
            job.completed_at = datetime.datetime.now()
            job.actual_duration = actual_duration

            # Ensure Redis also has completion data as soon as it's set in DB
            try:
                from utils.redis_job_store import RedisJobStore
                RedisJobStore.update_job(job_id, {
                    'completed_at': job.completed_at,
                    'output_filename': filename,
                    'output_file_size': output_file_size,
                    'page_count': page_count,
                    'actual_duration': actual_duration
                })
            except Exception as _:
                # Non-fatal if Redis is unavailable; broadcasting will still include DB fallback
                pass

            # Worker updates DB only, backend Celery event listener will broadcast
            change_status(job, JobStatus.COMPLETE, db, session_key, {
                'actual_duration': actual_duration,
                'output_file_size': output_file_size,
                'output_filename': filename,
                'page_count': page_count
            }, broadcast=False)

            # Calculate ETA accuracy
            eta_accuracy = None
            if job.projected_eta:
                eta_accuracy = (actual_duration / job.projected_eta) * 100

            db.commit()


    except Exception as e:
        log_with_context(
            logger, 'error', f'Conversion failed: {str(e)}',
            job_id=job_id,
            user_id=session_key,
            error_type=type(e).__name__,
            processing_time_seconds=(datetime.datetime.now() - start_time).total_seconds(),
            source='worker'
        )
        
        # Store errored input file in error bucket for debugging
        try:
            input_key = f"{alias}/{job_id}/input/{upload_name}"
            error_key = f"errors/{alias}/{job_id}/input/{upload_name}"
            s3_storage.copy_to_error_bucket(input_key, error_key)
            
            log_with_context(
                logger, 'info', f'Errored file stored in error bucket: {error_key}',
                job_id=job_id,
                user_id=session_key,
                error_bucket_key=error_key,
                source='worker'
            )
        except Exception as storage_error:
            log_with_context(
                logger, 'warning', f'Failed to store errored file in error bucket: {storage_error}',
                job_id=job_id,
                user_id=session_key,
                source='worker'
            )
        
        # Update job status to errored
        try:
            job = db.query(ConversionJob).get(job_id)
            if job:
                # Worker updates DB only, backend Celery event listener will broadcast
                change_status(job, JobStatus.ERRORED, db, session_key, {
                    'error_message': str(e),
                    'error_source': 'process_conversion'
                }, broadcast=False)
        except Exception as db_error:
            log_with_context(
                logger, 'error', f'Failed to update job status to errored: {db_error}',
                job_id=job_id,
                user_id=session_key,
                source='worker'
            )
    finally:
        # Clean up temporary upload directory for this job (always execute)
        temp_job_dir = os.path.join(UPLOADS_DIRECTORY, job_id)
        try:
            shutil.rmtree(temp_job_dir)
            log_with_context(
                logger, 'info', 'Cleaned up temporary files',
                job_id=job_id,
                user_id=session_key,
                temp_dir=temp_job_dir,
                source='worker'
            )
        except Exception as cleanup_err:
            log_with_context(
                logger, 'warning', f'Failed to remove temporary directory: {cleanup_err}',
                job_id=job_id,
                user_id=session_key,
                temp_dir=temp_job_dir,
                source='worker'
            )
        
        db.close()
