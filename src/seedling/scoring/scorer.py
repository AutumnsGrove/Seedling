"""Scoring module using OpenRouter/Kimi K2.5.

Two-pass scoring:
1. Quick reject (cheap, catches obvious mismatches)
2. Detailed scoring (nuanced evaluation for passing jobs)
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI


@dataclass
class ScoredJob:
    """Represents a job with scoring results."""

    url: str
    match_score: int  # 0-100 composite score
    category: str  # tech-cyber, tech-systems, tech-fullstack, tech-devops, serving
    score_breakdown: dict  # per-dimension scores
    score_summary: str  # 2-sentence "why this matched"
    quick_reject_reason: Optional[str] = None
    passed_quick_reject: bool = True


# Candidate profile for scoring context
CANDIDATE_PROFILE = """
Autumn Brown — Job Candidate Profile

EDUCATION
BS in Information Technology, focus Cybersecurity — Kennesaw State University, 2025

TECH SKILLS (strong)
- TypeScript, Python, Java
- Cloudflare Workers, Durable Objects, D1, KV, R2, Email Routing
- Full-stack web development (React, Tailwind, HTML/CSS)
- Systems programming, WebAssembly, MCP servers
- Built Grove: a multi-tenant SaaS platform with 60+ repositories
- Docker, Git, SQL

TECH SKILLS (familiar)
- Rust (learning), C#
- ML/AI: LLM inference (Ollama, LM Studio), transformer architecture, tool calling
- Security: Nmap, Wireshark, Kali Linux, network security, secure software dev, API security

EXPERIENCE
- Software Dev Intern — Marietta NDT (2019): C#, Python, backend systems, client GUI
- MineTicket Capstone — KSU (2024): Led Python team, MariaDB, security framework, auth
- Merchandise Execution Team — Home Depot (Mar 2024–Dec 2025)
- Merchandising — Costco Wholesale (Mar 2022–Oct 2023)
- Prepared Foods & Deli — Publix Greenwise Market (Nov 2020–Nov 2021)

CERTIFICATIONS
- Georgia Food Handler's Permit (current)

SEEKING
- Tech: Entry to mid-level. Remote preferred, Atlanta for onsite, open to relocation.
- Serving: Atlanta area. Fully open availability. Immediate start.

PORTFOLIO
- GitHub: @autumnsgrove (60+ repos)
- Grove platform: multi-tenant SaaS on Cloudflare infrastructure
"""


# Prompt templates
QUICK_REJECT_PROMPT = """\
You are a job matching assistant. Given this job listing, answer YES or NO for each question:

1. Does it require 3+ years of professional experience?
2. Is it a senior/staff/principal/director/manager level role?
3. Is the listed salary below $40k (tech) or below minimum wage (serving)?
4. Is the actual role significantly different from the title (e.g., "Security Analyst" that's really Help Desk)?
5. Does it require a specific certification I don't have (CISSP, CISM, etc.)?

Job listing:
{job_description}

Respond with EXACTLY one line in this format:
PASS or REJECT: <reason>
"""


TECH_SCORING_PROMPT = """\
You are a job matching assistant. Score this job listing for the candidate.

Candidate profile:
{candidate_profile}

Job listing:
{job_description}

Score on these dimensions (0-100 each):
1. Skill match: How well do my skills align with requirements?
2. Growth potential: Will this teach me things I want to learn (Rust, low-level systems, infrastructure)?
3. Logistics: Remote? Atlanta? Relocation support?
4. Compensation signal: Salary range when visible, company reputation as proxy
5. Application ease: Quick Apply? Long form? Portfolio required?

Respond with EXACTLY one JSON object, no other text:
{{"score": <0-100>, "category": "tech-cyber|tech-systems|tech-fullstack|tech-devops", "breakdown": {{"skill_match": <0-100>, "growth": <0-100>, "logistics": <0-100>, "compensation": <0-100>, "ease": <0-100>}}, "summary": "<2 sentences why this matched>"}}"""


SERVING_SCORING_PROMPT = """\
You are a job matching assistant. Score this serving job listing.

Candidate profile:
{candidate_profile}

Job listing:
{job_description}

Score on these dimensions (0-100 each):
1. Location: Distance from Smyrna/Atlanta area
2. Schedule: Flexible? Evenings/weekends? Part-time OK?
3. Pay signal: Base + tips potential, mentioned compensation
4. Vibe: Does the listing suggest a decent workplace?

Respond with EXACTLY one JSON object, no other text:
{{"score": <0-100>, "category": "serving", "breakdown": {{"location": <0-100>, "schedule": <0-100>, "pay": <0-100>, "vibe": <0-100>}}, "summary": "<2 sentences why this matched>"}}"""


class JobScorer:
    """Scores job listings using OpenRouter/Kimi K2.5."""

    def __init__(
        self,
        api_key: str,
        model: str = "moonshotai/kimi-k2.5",
        http_client=None,
    ) -> None:
        """Initialize the job scorer.

        Args:
            api_key: OpenRouter API key.
            model: Model to use for scoring.
            http_client: Optional HTTP client.
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            http_client=http_client,
        )
        self.model = model
        self.tech_threshold = 60
        self.serving_threshold = 50

    async def quick_reject(
        self, job_description: str
    ) -> tuple[bool, Optional[str]]:
        """Run quick reject pass.

        Args:
            job_description: Full job description.

        Returns:
            Tuple of (passed, reject_reason).
        """
        prompt = QUICK_REJECT_PROMPT.format(job_description=job_description)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=100,
        )

        raw_content = response.choices[0].message.content
        if raw_content is None:
            logging.warning("quick_reject: LLM returned None content")
            return False, "LLM returned empty response"
        content = raw_content.strip()

        if content.startswith("PASS"):
            return True, None

        # Extract reason after "REJECT: "
        if ":" in content:
            reason = content.split(":", 1)[1].strip()
            return False, reason

        return False, "Unknown reason"

    async def score_tech_job(
        self,
        job_description: str,
    ) -> ScoredJob:
        """Score a tech job.

        Args:
            job_description: Full job description.

        Returns:
            ScoredJob with scoring results.
        """
        prompt = TECH_SCORING_PROMPT.format(
            candidate_profile=CANDIDATE_PROFILE,
            job_description=job_description,
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )

        raw_content = response.choices[0].message.content
        if raw_content is None:
            logging.warning("score_tech_job: LLM returned None content")
            return ScoredJob(
                url="",
                match_score=0,
                category="tech-devops",
                score_breakdown={},
                score_summary="LLM returned empty response",
                quick_reject_reason=None,
                passed_quick_reject=True,
            )
        content = raw_content.strip()

        # Parse JSON response
        try:
            # Try to extract JSON from response
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
                data = json.loads(json_str)

                return ScoredJob(
                    url="",  # Will be set by caller
                    match_score=data["score"],
                    category=data["category"],
                    score_breakdown=data["breakdown"],
                    score_summary=data["summary"],
                    quick_reject_reason=None,
                    passed_quick_reject=True,
                )
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning(f"score_tech_job: Failed to parse JSON: {e}")

        # Fallback: parse raw response
        return ScoredJob(
            url="",
            match_score=0,
            category="tech-devops",
            score_breakdown={},
            score_summary="Could not parse scoring response",
            quick_reject_reason=None,
            passed_quick_reject=True,
        )

    async def score_serving_job(
        self,
        job_description: str,
    ) -> ScoredJob:
        """Score a serving job.

        Args:
            job_description: Full job description.

        Returns:
            ScoredJob with scoring results.
        """
        prompt = SERVING_SCORING_PROMPT.format(
            candidate_profile=CANDIDATE_PROFILE,
            job_description=job_description,
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )

        raw_content = response.choices[0].message.content
        if raw_content is None:
            logging.warning("score_serving_job: LLM returned None content")
            return ScoredJob(
                url="",
                match_score=0,
                category="serving",
                score_breakdown={},
                score_summary="LLM returned empty response",
                quick_reject_reason=None,
                passed_quick_reject=True,
            )
        content = raw_content.strip()

        # Parse JSON response
        try:
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
                data = json.loads(json_str)

                return ScoredJob(
                    url="",
                    match_score=data["score"],
                    category="serving",
                    score_breakdown=data["breakdown"],
                    score_summary=data["summary"],
                    quick_reject_reason=None,
                    passed_quick_reject=True,
                )
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning(f"score_serving_job: Failed to parse JSON: {e}")

        # Fallback
        return ScoredJob(
            url="",
            match_score=0,
            category="serving",
            score_breakdown={},
            score_summary="Could not parse scoring response",
            quick_reject_reason=None,
            passed_quick_reject=True,
        )

    async def score_job(
        self,
        job_description: str,
        category: str,
    ) -> ScoredJob:
        """Score a job based on category.

        Args:
            job_description: Full job description.
            category: Job category (tech-*, serving).

        Returns:
            ScoredJob with scoring results.
        """
        if category == "serving":
            return await self.score_serving_job(job_description)
        else:
            return await self.score_tech_job(job_description)


async def score_job(
    job_description: str,
    api_key: str,
    category: str = "tech-devops",
    model: str = "moonshotai/kimi-k2.5",
) -> ScoredJob:
    """Score a single job.

    Convenience function.

    Args:
        job_description: Full job description.
        api_key: OpenRouter API key.
        category: Job category.
        model: Model to use.

    Returns:
        ScoredJob instance.
    """
    scorer = JobScorer(api_key=api_key, model=model)
    return await scorer.score_job(job_description, category)


async def quick_reject_job(
    job_description: str,
    api_key: str,
    model: str = "moonshotai/kimi-k2.5",
) -> tuple[bool, Optional[str]]:
    """Quick reject a job.

    Args:
        job_description: Full job description.
        api_key: OpenRouter API key.
        model: Model to use.

    Returns:
        Tuple of (passed, reject_reason).
    """
    scorer = JobScorer(api_key=api_key, model=model)
    return await scorer.quick_reject(job_description)
