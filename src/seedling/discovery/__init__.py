"""Job discovery module.

Primary discovery engine: JobSpy (python-jobspy)
Scrapes Indeed, Google Jobs, LinkedIn, Glassdoor, ZipRecruiter.
"""

from seedling.discovery.jobspy import (
    DiscoveredJob,
    JobSpyDiscovery,
    SearchConfig,
    generate_url_hash,
)

__all__ = [
    "DiscoveredJob",
    "JobSpyDiscovery",
    "SearchConfig",
    "generate_url_hash",
]
