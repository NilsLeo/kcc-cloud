"""Tests for ConversionJob model."""

from datetime import datetime
from database.models import ConversionJob, JobStatus


class TestConversionJob:
    """Test ConversionJob model."""

    def test_job_creation(self):
        """Test basic job creation."""
        job = ConversionJob(
            id="test-job-123",
            status=JobStatus.QUEUED,
            input_filename="test.cbz",
            device_profile="KV",
        )

        assert job.id == "test-job-123"
        assert job.status == JobStatus.QUEUED
        assert job.input_filename == "test.cbz"
        assert job.device_profile == "KV"

    def test_job_status_transitions(self):
        """Test job status can be updated."""
        job = ConversionJob(id="test-job-789", status=JobStatus.QUEUED, input_filename="test.epub")

        # Transition to PROCESSING
        job.status = JobStatus.PROCESSING
        assert job.status == JobStatus.PROCESSING

        # Transition to COMPLETE
        job.status = JobStatus.COMPLETE
        assert job.status == JobStatus.COMPLETE

    def test_job_timestamps(self):
        """Test that timestamps can be set."""
        job = ConversionJob(
            id="test-job-timestamps", input_filename="test.cbz", status=JobStatus.QUEUED
        )

        now = datetime.utcnow()
        job.queued_at = now
        job.processing_at = now
        job.completed_at = now

        assert job.queued_at == now
        assert job.processing_at == now
        assert job.completed_at == now

    def test_job_file_sizes(self):
        """Test that file sizes can be stored."""
        job = ConversionJob(
            id="test-job-sizes",
            input_filename="test.cbz",
            input_file_size=1024000,
            output_file_size=512000,
        )

        assert job.input_file_size == 1024000
        assert job.output_file_size == 512000

    def test_job_error_handling(self):
        """Test that error information can be stored."""
        job = ConversionJob(
            id="test-job-error",
            input_filename="test.cbz",
            status=JobStatus.ERRORED,
            error_message="Test error message",
        )

        assert job.status == JobStatus.ERRORED
        assert job.error_message == "Test error message"
