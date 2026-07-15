"""Tests for KCC stdout progress parsing."""

from utils.kcc_progress import (
    parse_progress_line,
    phase_ceiling,
    MAX_PROGRESS,
    PHASE_MARKERS,
)


class TestParseProgressLine:
    """parse_progress_line maps real KCC stdout lines to (percent, phase)."""

    def test_no_marker_returns_none(self):
        assert parse_progress_line("some unrelated log line") is None
        assert parse_progress_line("") is None
        assert parse_progress_line(None) is None
        assert parse_progress_line("   ") is None

    def test_preparing_phase(self):
        assert parse_progress_line("Preparing source images...") == (3, "Preparing")
        assert parse_progress_line("Checking images...") == (8, "Preparing")

    def test_processing_phase(self):
        assert parse_progress_line("Processing images...") == (15, "Converting")

    def test_no_processing_mode(self):
        # KCC prints this when the "no processing" option is set.
        line = "Do not process image, ignore any profile or processing option"
        assert parse_progress_line(line) == (15, "Converting")

    def test_optimizing_marker(self):
        assert parse_progress_line("imgFileProcessing: 12.3 seconds") == (78, "Optimizing")

    def test_packaging_markers(self):
        assert parse_progress_line("Creating CBZ file...") == (85, "Packaging")
        assert parse_progress_line("Creating EPUB file...") == (85, "Packaging")
        assert parse_progress_line("Creating PDF file with PyMuPDF...") == (85, "Packaging")
        assert parse_progress_line("Creating MOBI files...") == (88, "Packaging")

    def test_finalizing_marker(self):
        assert parse_progress_line("makeZIP time: 1.2 seconds") == (95, "Finalizing")

    def test_case_insensitive_and_multifile_prefix(self):
        # KCC prepends a "[1/3] " style prefix for multi-file jobs.
        assert parse_progress_line("[2/5] Processing images...") == (15, "Converting")
        assert parse_progress_line("PROCESSING IMAGES...") == (15, "Converting")

    def test_markers_are_ascending(self):
        percents = [p for _m, p, _phase in PHASE_MARKERS]
        assert percents == sorted(percents)


class TestPhaseCeiling:
    """phase_ceiling bounds the activity-gated creep within a phase."""

    def test_ceiling_is_next_marker(self):
        # At the start of "Processing images" (15), the next milestone is 78.
        assert phase_ceiling(15) == 78

    def test_ceiling_of_preparing(self):
        assert phase_ceiling(3) == 8

    def test_ceiling_past_last_marker_is_max(self):
        assert phase_ceiling(95) == MAX_PROGRESS
        assert phase_ceiling(99) == MAX_PROGRESS

    def test_ceiling_at_zero(self):
        # Before any marker, the next milestone is the first phase.
        assert phase_ceiling(0) == 3
