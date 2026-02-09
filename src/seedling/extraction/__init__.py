"""Job extraction module using Shutter.

Extracts structured data from job listing URLs.
"""

from seedling.extraction.shutter import (
    DEFAULT_JOB_QUERY,
    ExtractedJob,
    extract_job,
    extract_job_async,
    extract_with_shutter,
    extract_with_shutter_async,
    find_shutter_executable,
)

__all__ = [
    "ExtractedJob",
    "DEFAULT_JOB_QUERY",
    "extract_job",
    "extract_job_async",
    "extract_with_shutter",
    "extract_with_shutter_async",
    "find_shutter_executable",
]
