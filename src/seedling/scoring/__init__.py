"""Job scoring module using OpenRouter/Kimi K2.5.

Two-pass scoring:
1. Quick reject (cheap, catches obvious mismatches)
2. Detailed scoring (nuanced evaluation for passing jobs)
"""

from seedling.scoring.scorer import (
    CANDIDATE_PROFILE,
    JobScorer,
    QUICK_REJECT_PROMPT,
    SERVING_SCORING_PROMPT,
    TECH_SCORING_PROMPT,
    ScoredJob,
    quick_reject_job,
    score_job,
)

__all__ = [
    "CANDIDATE_PROFILE",
    "JobScorer",
    "QUICK_REJECT_PROMPT",
    "SERVING_SCORING_PROMPT",
    "TECH_SCORING_PROMPT",
    "ScoredJob",
    "quick_reject_job",
    "score_job",
]
