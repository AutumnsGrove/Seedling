"""Resume tailoring module.

Generates tailored resumes and cover letters using Jinja2, Playwright, and R2.
"""

from seedling.tailoring.tailor import (
    BASE_SERVING_RESUME,
    BASE_TECH_RESUME,
    R2Uploader,
    ResumeTailor,
    TailoredCoverLetter,
    TailoredResume,
)

__all__ = [
    "BASE_SERVING_RESUME",
    "BASE_TECH_RESUME",
    "R2Uploader",
    "ResumeTailor",
    "TailoredCoverLetter",
    "TailoredResume",
]
