"""Local filesystem storage implementation to replace S3/MinIO."""
import os
import shutil
from pathlib import Path


class LocalStorage:
    """Local filesystem storage for uploads and outputs."""

    def __init__(self, base_path='/data'):
        """
        Initialize local storage.

        Args:
            base_path: Base directory for all file storage
        """
        self.base_path = Path(base_path)
        self.uploads_path = self.base_path / 'uploads'
        self.outputs_path = self.base_path / 'outputs'

        # Create directories if they don't exist
        self.uploads_path.mkdir(parents=True, exist_ok=True)
        self.outputs_path.mkdir(parents=True, exist_ok=True)

    def upload_file(self, file_obj, job_id, filename):
        """
        Save uploaded file to local filesystem.

        Args:
            file_obj: File-like object or path to file
            job_id: UUID of the conversion job
            filename: Original filename

        Returns:
            str: Path to saved file
        """
        job_upload_dir = self.uploads_path / job_id
        job_upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = job_upload_dir / filename

        # Handle different file object types
        if isinstance(file_obj, (str, Path)):
            # It's a file path, copy it
            shutil.copy2(file_obj, file_path)
        elif hasattr(file_obj, 'save'):
            # It's a Flask/Werkzeug FileStorage object
            file_obj.save(str(file_path))
        elif hasattr(file_obj, 'read'):
            # It's a file-like object
            with open(file_path, 'wb') as f:
                f.write(file_obj.read())
        else:
            raise ValueError(f"Unsupported file object type: {type(file_obj)}")

        return str(file_path)

    def get_upload_path(self, job_id):
        """
        Get path to uploaded file for a job.

        Args:
            job_id: UUID of the conversion job

        Returns:
            str: Path to upload directory or None if not found
        """
        job_upload_dir = self.uploads_path / job_id
        if not job_upload_dir.exists():
            return None

        # Return the first file in the directory
        files = list(job_upload_dir.iterdir())
        if not files:
            return None

        return str(files[0])

    def save_output(self, source_path, job_id, output_filename):
        """
        Save converted output file.

        Args:
            source_path: Path to the converted file
            job_id: UUID of the conversion job
            output_filename: Name for the output file

        Returns:
            str: Path to saved output file
        """
        job_output_dir = self.outputs_path / job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)

        output_path = job_output_dir / output_filename

        if isinstance(source_path, (str, Path)):
            shutil.copy2(source_path, output_path)
        else:
            raise ValueError(f"Unsupported source path type: {type(source_path)}")

        return str(output_path)

    def get_output_path(self, job_id):
        """
        Get path to output file for a job.

        Args:
            job_id: UUID of the conversion job

        Returns:
            str: Path to output file or None if not found
        """
        job_output_dir = self.outputs_path / job_id
        if not job_output_dir.exists():
            return None

        # Return the first file in the directory
        files = list(job_output_dir.iterdir())
        if not files:
            return None

        return str(files[0])

    def delete_upload(self, job_id):
        """
        Delete uploaded file(s) for a job.

        Args:
            job_id: UUID of the conversion job
        """
        job_upload_dir = self.uploads_path / job_id
        if job_upload_dir.exists():
            shutil.rmtree(job_upload_dir)

    def delete_output(self, job_id):
        """
        Delete output file(s) for a job.

        Args:
            job_id: UUID of the conversion job
        """
        job_output_dir = self.outputs_path / job_id
        if job_output_dir.exists():
            shutil.rmtree(job_output_dir)

    def delete_job_files(self, job_id):
        """
        Delete all files (uploads and outputs) for a job.

        Args:
            job_id: UUID of the conversion job
        """
        self.delete_upload(job_id)
        self.delete_output(job_id)

    def get_download_url(self, job_id):
        """
        Get download URL for output file.

        Args:
            job_id: UUID of the conversion job

        Returns:
            str: Download URL path (relative, to be used with Flask route)
        """
        return f"/download/{job_id}"

    def get_file_size(self, file_path):
        """
        Get size of a file in bytes.

        Args:
            file_path: Path to the file

        Returns:
            int: File size in bytes, or None if file doesn't exist
        """
        path = Path(file_path)
        if path.exists():
            return path.stat().st_size
        return None


# Global storage instance
storage = LocalStorage(base_path=os.getenv('STORAGE_PATH', '/data'))
