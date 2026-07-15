"""
Parse real conversion progress from KCC's stdout.

KCC's CLI prints ordered phase markers as it works through a conversion
(preparing the workspace, processing the page images, packaging the output).
We map those markers to a monotonic progress percentage and a human-readable
phase label so the frontend can render *real* backend progress instead of a
client-side simulation derived from a single up-front ETA estimate.

Note: KCC only emits per-page progress ticks in GUI mode. On the CLI it prints
phase-level markers only, so backend progress is phase-granular by design. The
long "Processing images" phase is silent on stdout, so callers should treat
on-disk activity (not stdout silence) as the liveness signal while it runs.
"""

from typing import List, Optional, Tuple

# Ordered (marker substring, percent, phase label), ascending by percent.
# The substring is matched case-insensitively against each stdout line, so the
# optional multi-file "[1/3] " prefix KCC prepends does not affect matching.
# Progress is clamped to be monotonic by the caller, so a stray out-of-order
# line can never move the bar backwards.
PHASE_MARKERS: List[Tuple[str, int, str]] = [
    ("preparing source images", 3, "Preparing"),
    ("checking images", 8, "Preparing"),
    ("do not process image", 15, "Converting"),
    ("processing images", 15, "Converting"),
    ("imgfileprocessing:", 78, "Optimizing"),
    ("creating cbz file", 85, "Packaging"),
    ("creating epub file", 85, "Packaging"),
    ("creating pdf file", 85, "Packaging"),
    ("creating mobi files", 88, "Packaging"),
    ("makezip time", 95, "Finalizing"),
]

# Percentage ceiling for any phase; the bar only reaches 100% on COMPLETE.
MAX_PROGRESS = 99


def parse_progress_line(line: Optional[str]) -> Optional[Tuple[int, str]]:
    """
    Map a single KCC stdout line to (percent, phase_label).

    Returns None when the line contains no recognised phase marker.
    """
    if not line:
        return None
    text = line.strip().lower()
    if not text:
        return None
    for marker, percent, phase in PHASE_MARKERS:
        if marker in text:
            return (percent, phase)
    return None


def phase_ceiling(percent: int) -> int:
    """
    Return the percentage of the next phase above ``percent``.

    Used to bound the activity-gated creep so it advances *within* the current
    phase but never jumps ahead of the next real milestone.
    """
    for _marker, marker_percent, _phase in PHASE_MARKERS:
        if marker_percent > percent:
            return marker_percent
    return MAX_PROGRESS
