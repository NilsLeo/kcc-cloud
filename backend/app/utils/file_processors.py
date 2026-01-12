import glob
import os
import shutil
import subprocess
import zipfile

from utils.enhanced_logger import setup_enhanced_logging, log_with_context

# Initialize logging
logger = setup_enhanced_logging()

# Supported archive extensions
ARCHIVE_EXTENSIONS = {'.zip', '.cbz', '.rar', '.cbr', '.7z', '.cb7'}


def process_7z(file_path: str, temp_dir: str, job_id: str = None, user_id: str = None) -> str:
    """Process a 7Z/CB7 file and return the extracted directory path."""
    try:
        # Get the base name of the input file
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        # Create nested directory with same name
        nested_dir = os.path.join(temp_dir, base_name)
        os.makedirs(nested_dir, exist_ok=True)

        result = subprocess.run(
            ["7z", "x", f"-o{nested_dir}", file_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise Exception(f"7z extraction failed: {result.stderr}")

        file_count = len(
            [
                f
                for f in glob.glob(os.path.join(nested_dir, "**/*.*"), recursive=True)
                if os.path.isfile(f)
            ]
        )
        log_with_context(
            logger, 'info', f'Successfully extracted 7Z/CB7 with {file_count} files to {nested_dir}',
            job_id=job_id,
            user_id=user_id,
            file_path=file_path,
            file_count=file_count,
            extraction_type='7z'
        )
        return nested_dir
    except Exception as e:
        raise Exception(f"Failed to process 7Z/CB7: {str(e)}")


def process_zip(file_path: str, temp_dir: str, job_id: str = None, user_id: str = None) -> str:
    """Process a ZIP/CBZ file and return the extracted directory path."""
    try:
        # Get the base name of the input file
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        # Create nested directory with same name
        nested_dir = os.path.join(temp_dir, base_name)
        os.makedirs(nested_dir, exist_ok=True)

        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(nested_dir)

        # Use the nested directory as manga_dir
        manga_dir = nested_dir

        file_count = len(
            [
                f
                for f in glob.glob(os.path.join(manga_dir, "**/*.*"), recursive=True)
                if os.path.isfile(f)
            ]
        )
        log_with_context(
            logger, 'info', f'Successfully extracted ZIP/CBZ with {file_count} files to {manga_dir}',
            job_id=job_id,
            user_id=user_id,
            file_path=file_path,
            file_count=file_count,
            extraction_type='zip'
        )
        return manga_dir
    except Exception as e:
        raise Exception(f"Failed to process ZIP/CBZ: {str(e)}")


def process_rar(file_path: str, temp_dir: str, job_id: str = None, user_id: str = None) -> str:
    """Process a RAR/CBR file and return the extracted directory path."""
    try:
        # Get the base name of the input file
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        # Create nested directory with same name
        nested_dir = os.path.join(temp_dir, base_name)
        os.makedirs(nested_dir, exist_ok=True)

        if shutil.which("unrar"):
            result = subprocess.run(
                ["unrar", "x", file_path, nested_dir], capture_output=True, text=True
            )
            if result.returncode != 0:
                raise Exception(f"unrar failed: {result.stderr}")
        else:
            result = subprocess.run(
                ["7z", "x", f"-o{nested_dir}", file_path],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise Exception(f"7z extraction failed: {result.stderr}")

        file_count = len(
            [
                f
                for f in glob.glob(os.path.join(nested_dir, "**/*.*"), recursive=True)
                if os.path.isfile(f)
            ]
        )
        log_with_context(
            logger, 'info', f'Successfully extracted RAR/CBR with {file_count} files to {nested_dir}',
            job_id=job_id,
            user_id=user_id,
            file_path=file_path,
            file_count=file_count,
            extraction_type='rar'
        )
        return nested_dir
    except Exception as e:
        raise Exception(f"Failed to process RAR/CBR: {str(e)}")


def unwrap_nested_archives(extracted_dir: str, job_id: str = None, user_id: str = None, max_depth: int = 10) -> str:
    """
    Recursively unwrap nested archives until we reach actual content.

    If an extracted archive contains only a single file and that file is another archive,
    extract it and continue until we find actual content (images, multiple files, etc).

    Args:
        extracted_dir: Directory containing extracted files
        job_id: Job ID for logging
        user_id: User ID for logging
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Path to the directory containing the final unwrapped content
    """
    depth = 0
    current_dir = extracted_dir

    while depth < max_depth:
        # Get all files in the current directory (recursively)
        all_files = [
            f for f in glob.glob(os.path.join(current_dir, "**/*"), recursive=True)
            if os.path.isfile(f)
        ]

        # If directory is empty, something went wrong
        if not all_files:
            log_with_context(
                logger, 'warning', f'Nested archive unwrapping stopped: directory is empty',
                job_id=job_id,
                user_id=user_id,
                current_dir=current_dir,
                depth=depth
            )
            break

        # If there's more than one file, we've reached actual content
        if len(all_files) > 1:
            log_with_context(
                logger, 'info', f'Nested archive unwrapping complete: found {len(all_files)} files',
                job_id=job_id,
                user_id=user_id,
                final_dir=current_dir,
                file_count=len(all_files),
                unwrap_depth=depth
            )
            break

        # There's exactly one file - check if it's an archive
        single_file = all_files[0]
        file_ext = os.path.splitext(single_file)[1].lower()

        # If the single file is not an archive, we've reached content
        if file_ext not in ARCHIVE_EXTENSIONS:
            log_with_context(
                logger, 'info', f'Nested archive unwrapping complete: single non-archive file found',
                job_id=job_id,
                user_id=user_id,
                final_dir=current_dir,
                file_name=os.path.basename(single_file),
                file_ext=file_ext,
                unwrap_depth=depth
            )
            break

        # The single file is another archive - extract it!
        log_with_context(
            logger, 'info', f'Found nested archive: {os.path.basename(single_file)} - extracting...',
            job_id=job_id,
            user_id=user_id,
            nested_archive=os.path.basename(single_file),
            archive_type=file_ext,
            unwrap_depth=depth
        )

        # Create a new extraction directory
        parent_dir = os.path.dirname(current_dir)
        new_extract_dir = os.path.join(parent_dir, f"unwrapped_{depth + 1}")
        os.makedirs(new_extract_dir, exist_ok=True)

        # Extract based on file type
        try:
            if file_ext in {'.zip', '.cbz'}:
                nested_dir = process_zip(single_file, new_extract_dir, job_id=job_id, user_id=user_id)
            elif file_ext in {'.rar', '.cbr'}:
                nested_dir = process_rar(single_file, new_extract_dir, job_id=job_id, user_id=user_id)
            elif file_ext in {'.7z', '.cb7'}:
                nested_dir = process_7z(single_file, new_extract_dir, job_id=job_id, user_id=user_id)
            else:
                # Should not happen due to earlier check, but just in case
                break

            # Move to the newly extracted directory
            current_dir = nested_dir
            depth += 1

        except Exception as e:
            log_with_context(
                logger, 'error', f'Failed to extract nested archive: {str(e)}',
                job_id=job_id,
                user_id=user_id,
                nested_archive=os.path.basename(single_file),
                error_type=type(e).__name__
            )
            # Return current directory if extraction fails
            break

    if depth >= max_depth:
        log_with_context(
            logger, 'warning', f'Nested archive unwrapping stopped: max depth ({max_depth}) reached',
            job_id=job_id,
            user_id=user_id,
            current_dir=current_dir
        )

    return current_dir


