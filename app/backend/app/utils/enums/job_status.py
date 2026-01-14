from enum import Enum


class JobStatus(Enum):
    """Enum for conversion job status values."""

    # Active/Processing States
    QUEUED = "QUEUED"        # Job created and waiting to be processed (initial state)
    UPLOADING = "UPLOADING"  # File is currently being uploaded to the server
    PROCESSING = "PROCESSING" # File upload complete, conversion actively running with KCC

    # Success States
    COMPLETE = "COMPLETE"    # Conversion finished successfully, output file ready for download
    DOWNLOADED = "DOWNLOADED" # User has successfully downloaded the converted file (final success state)

    # Failure States
    ERRORED = "ERRORED"      # Conversion failed due to processing error (bad file, format issues, etc.)
    CANCELLED = "CANCELLED"  # Job was manually cancelled by user
    ABANDONED = "ABANDONED"  # Job was automatically cancelled due to timeout or abandonment
