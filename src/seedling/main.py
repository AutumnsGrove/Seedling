"""Main entry point for Seedling.

Orchestrates the complete pipeline: discover → extract → score → tailor → notify.
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from nanoid import generate

from seedling.config import load_secrets
from seedling.db import Database, Job, Run, get_database
from seedling.discovery.jobspy import JobSpyDiscovery, generate_url_hash
from seedling.extraction.shutter import (
    ExtractedJob,
    extract_job_async,
    DEFAULT_JOB_QUERY,
)
from seedling.scoring.scorer import (
    JobScorer,
    ScoredJob,
)
from seedling.tailoring.tailor import (
    ResumeTailor,
    R2Uploader,
)
from seedling.notify.digest import (
    DigestJob,
    DigestStats,
    create_digest_jobs_from_db_jobs,
    send_digest,
)

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Seedling - Local Job Scout & Resume Tailor"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover + extract + score, but don't email",
    )
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="Re-score already extracted jobs",
    )
    parser.add_argument(
        "--email-only",
        action="store_true",
        help="Re-send last digest",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to secrets.json",
    )

    return parser.parse_args()


def _infer_category(job: Job) -> str:
    """Infer job category from title and description.

    Args:
        job: Job to categorize.

    Returns:
        Category string.
    """
    text = f"{job.title or ''} {job.description or ''}".lower()

    # Serving keywords — specific to food service, not generic "server"
    serving_keywords = [
        "restaurant server", "food server", "bartender", "barista",
        "hostess", "food runner", "busser", "waitstaff", "waitress",
        "waiter", "dining", "food service", "dishwasher", "line cook",
        "prep cook", "host/hostess", "catering",
    ]
    if any(kw in text for kw in serving_keywords):
        return "serving"

    # Tech subcategories — checked after serving to avoid false positives
    if "security" in text or "cyber" in text or "soc analyst" in text:
        return "tech-cyber"
    elif "systems" in text or "infrastructure" in text or "platform" in text:
        return "tech-systems"
    elif "full stack" in text or "fullstack" in text or "frontend" in text or "backend" in text:
        return "tech-fullstack"
    elif "devops" in text or "sre" in text or "site reliability" in text:
        return "tech-devops"

    return "tech-devops"  # Default


def _calc_stats(jobs: list[Job]) -> DigestStats:
    """Calculate stats for digest.

    Args:
        jobs: List of jobs.

    Returns:
        DigestStats instance.
    """
    return DigestStats(
        total_discovered=len(jobs),
        total_extracted=sum(1 for j in jobs if j.extracted_at),
        total_rejected=sum(1 for j in jobs if j.status == "rejected"),
        total_qualified=sum(1 for j in jobs if j.status in ["qualified", "emailed"]),
        tech_count=sum(1 for j in jobs if j.category and j.category.startswith("tech")),
        serving_count=sum(1 for j in jobs if j.category == "serving"),
    )


def _get_rejected_summary(db: Database) -> str:
    """Get summary of rejected jobs.

    Args:
        db: Database instance.

    Returns:
        Summary string.
    """
    today_rejected = db.get_jobs_by_status("rejected", limit=10)
    if not today_rejected:
        return "No jobs rejected today."

    reasons: dict[str, int] = {}
    for job in today_rejected:
        reason = job.quick_reject_reason or "Unknown"
        reasons[reason] = reasons.get(reason, 0) + 1

    lines = ["Rejection reasons:"]
    for reason, count in sorted(reasons.items(), key=lambda x: -x[1]):
        lines.append(f"  - {reason}: {count}")

    return "\n".join(lines)


async def run_pipeline(
    dry_run: bool = False,
    score_only: bool = False,
    email_only: bool = False,
    config_path: Path | None = None,
) -> None:
    """Run the complete Seedling pipeline.

    Args:
        dry_run: If True, skip email sending.
        score_only: If True, only score already extracted jobs.
        email_only: If True, only send the digest email.
        config_path: Optional path to secrets.json.
    """
    now = datetime.now(timezone.utc)
    start_time = now
    run_id = generate(size=12)

    print(f"🌱 Seedling v0.1.0 - {now.strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"   Run ID: {run_id}")
    print()

    # Load secrets
    try:
        secrets = load_secrets(config_path)
        print(f"✓ Loaded secrets for {secrets['SEEDLING_EMAIL']}")
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        print("\nPlease create ~/.seedling/secrets.json from secrets_template.json")
        sys.exit(1)
    except KeyError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)

    # Initialize database
    db = get_database()
    print(f"✓ Database initialized at {db.db_path}")

    # Create run record
    run = Run(id=run_id, started_at=start_time.isoformat())
    db.create_run(run)
    errors: list[str] = []
    stats = {
        "discovered": 0,
        "extracted": 0,
        "quick_rejected": 0,
        "scored": 0,
        "qualified": 0,
        "resumes": 0,
    }

    try:
        # Phase 1: Discovery (unless score_only or email_only)
        if not score_only and not email_only:
            print("\n📡 Phase 1: Discovery")
            print("   (Searching via JobSpy — Indeed + Google Jobs)")

            try:
                discovery = JobSpyDiscovery()
                discovered_jobs = await discovery.discover_all_async()

                # Deduplicate against database and save
                new_count = 0
                for job in discovered_jobs:
                    url_hash = generate_url_hash(job.url)
                    existing = db.get_job_by_url_hash(url_hash)
                    if existing is None:
                        db_job = Job(
                            id=generate(size=8),
                            platform=job.platform,
                            url=job.url,
                            url_hash=url_hash,
                            title=job.title,
                            company=job.company,
                            location=job.location,
                            remote=job.is_remote,
                            salary_min=job.salary_min,
                            salary_max=job.salary_max,
                            description=job.description,
                            discovered_at=datetime.now(timezone.utc).isoformat(),
                            status="discovered",
                        )
                        db.upsert_job(db_job)
                        new_count += 1

                stats["discovered"] = new_count
                print(f"   ✓ Found {len(discovered_jobs)} total, {new_count} new jobs")

            except Exception as e:
                error_msg = f"Discovery failed: {e}"
                errors.append(error_msg)
                print(f"   ✗ {error_msg}")

        # Phase 2: Extraction (unless email_only)
        if not email_only:
            print("\n🔍 Phase 2: Extraction")

            jobs_to_extract = db.get_jobs_by_status("discovered", limit=50)

            if not jobs_to_extract:
                print("   (No jobs to extract)")
            else:
                for job in jobs_to_extract:
                    # JobSpy provides full descriptions — skip Shutter for those
                    if job.description and len(job.description) > 200:
                        job.extracted_at = datetime.now(timezone.utc).isoformat()
                        job.status = "extracted"
                        db.upsert_job(job)
                        stats["extracted"] += 1
                        print(f"   ✓ {(job.title or 'Unknown')[:35]} (full description)")
                    else:
                        # Short/missing description — try Shutter
                        try:
                            extracted = await extract_job_async(
                                url=job.url,
                                query=DEFAULT_JOB_QUERY,
                                model="accurate",
                            )

                            job.title = extracted.title or job.title
                            job.company = extracted.company or job.company
                            job.location = extracted.location or job.location
                            job.remote = extracted.remote or False
                            job.salary_min = extracted.salary_min
                            job.salary_max = extracted.salary_max
                            job.salary_text = extracted.salary_text
                            job.description = extracted.description or job.description
                            job.requirements = extracted.requirements
                            job.preferred = extracted.preferred
                            job.extracted_at = datetime.now(timezone.utc).isoformat()
                            job.status = "extracted"
                            job.shutter_pi_detected = extracted.pi_detected

                            db.upsert_job(job)
                            stats["extracted"] += 1
                            print(f"   ✓ {(job.title or 'Unknown')[:35]} (Shutter)")

                        except Exception as e:
                            error_msg = f"Extraction failed for {job.url}: {e}"
                            errors.append(error_msg)
                            print(f"   ✗ {str(e)[:60]}...")

                print(f"   ✓ Extracted {stats['extracted']} jobs")

        # Phase 3: Scoring (unless email_only)
        if not email_only:
            print("\n📊 Phase 3: Scoring")
            print("   (Scoring jobs using Kimi K2.5)")

            scorer = JobScorer(api_key=secrets["OPENROUTER_API_KEY"])

            jobs_to_score = db.get_jobs_by_status("extracted", limit=50)

            for db_job in jobs_to_score:
                try:
                    # Determine category from title/description
                    category = _infer_category(db_job)

                    # Run quick reject first
                    description = db_job.description or ""
                    passed, reject_reason = await scorer.quick_reject(description)

                    if not passed:
                        db_job.status = "rejected"
                        db_job.quick_reject_reason = reject_reason
                        db_job.category = category
                        db_job.scored_at = datetime.now(timezone.utc).isoformat()
                        stats["quick_rejected"] += 1
                        db.upsert_job(db_job)
                        print(f"   ✗ {(db_job.title or 'Unknown')[:35]} - rejected")
                        continue

                    # Score the job
                    scored = await scorer.score_job(description, category)

                    db_job.match_score = scored.match_score
                    db_job.category = scored.category
                    db_job.score_breakdown = json.dumps(scored.score_breakdown)
                    db_job.score_summary = scored.score_summary
                    db_job.scored_at = datetime.now(timezone.utc).isoformat()

                    # Determine if qualified
                    threshold = scorer.serving_threshold if category == "serving" else scorer.tech_threshold
                    if scored.match_score >= threshold:
                        db_job.status = "qualified"
                        stats["qualified"] += 1
                        print(f"   ✓ {(db_job.title or 'Unknown')[:35]} - {scored.match_score}pts")
                    else:
                        db_job.status = "scored"  # Scored but not qualified
                        print(f"   ~ {(db_job.title or 'Unknown')[:35]} - {scored.match_score}pts (below threshold)")

                    stats["scored"] += 1
                    db.upsert_job(db_job)

                except Exception as e:
                    error_msg = f"Scoring failed for {db_job.url}: {e}"
                    errors.append(error_msg)
                    print(f"   ✗ Scoring error: {str(e)[:50]}")

            print(f"   ✓ Scored {stats['scored']} jobs ({stats['qualified']} qualified, {stats['quick_rejected']} rejected)")

        # Phase 4: Tailoring (unless score_only or email_only)
        if not score_only and not email_only:
            print("\n📝 Phase 4: Tailoring")
            print("   (Generating tailored resumes)")

            qualified_jobs = db.get_qualified_jobs(days=1)

            if qualified_jobs:
                # Setup R2 uploader
                r2_uploader = R2Uploader(
                    account_id=secrets["R2_ACCOUNT_ID"],
                    access_key_id=secrets["R2_ACCESS_KEY_ID"],
                    secret_access_key=secrets["R2_SECRET_ACCESS_KEY"],
                    bucket=secrets["R2_BUCKET"],
                    public_url=secrets.get("R2_PUBLIC_URL", ""),
                )

                tailor = ResumeTailor(
                    api_key=secrets["OPENROUTER_API_KEY"],
                )

                for db_job in qualified_jobs:
                    try:
                        print(f"   Tailoring for {(db_job.title or 'Unknown')[:30]}...")

                        # Generate resume
                        if db_job.category == "serving":
                            resume = await tailor.tailor_serving_resume(
                                job_id=db_job.id,
                            )
                        else:
                            resume = await tailor.tailor_tech_resume(
                                job_id=db_job.id,
                                job_description=db_job.description or "",
                                category=db_job.category or "tech",
                            )

                        # Upload to R2
                        if db_job.category == "serving":
                            r2_url = r2_uploader.upload_serving_resume(resume)
                        else:
                            r2_url = r2_uploader.upload_resume(resume)

                        db_job.resume_r2_url = r2_url
                        stats["resumes"] += 1

                        # Optionally generate cover letter
                        if db_job.cover_letter_requested:
                            cover_letter = await tailor.generate_cover_letter(
                                job_id=db_job.id,
                                job_description=db_job.description or "",
                            )
                            if cover_letter:
                                cl_url = r2_uploader.upload_cover_letter(cover_letter)
                                db_job.cover_letter_r2_url = cl_url

                        db.upsert_job(db_job)
                        print(f"   ✓ {(db_job.title or 'Unknown')[:30]} - uploaded")

                    except Exception as e:
                        error_msg = f"Tailoring failed for {db_job.id}: {e}"
                        errors.append(error_msg)
                        print(f"   ✗ {error_msg[:50]}")

            print(f"   ✓ Generated {stats['resumes']} resumes")

        # Phase 5: Notification (unless dry_run)
        if not dry_run:
            print("\n📧 Phase 5: Notification")
            print("   (Sending digest email)")

            # Get today's qualified jobs
            todays_jobs = db.get_todays_jobs()

            if todays_jobs:
                # Convert to digest jobs
                digest_jobs = create_digest_jobs_from_db_jobs(todays_jobs)

                # Send email
                success = await send_digest(
                    jobs=digest_jobs,
                    stats=_calc_stats(todays_jobs),
                    rejected_summary=_get_rejected_summary(db),
                    zephyr_url=secrets["ZEPHYR_URL"],
                    zephyr_api_key=secrets["ZEPHYR_API_KEY"],
                    to_email=secrets["SEEDLING_EMAIL"],
                )

                if success:
                    print(f"   ✓ Email sent to {secrets['SEEDLING_EMAIL']}")
                    # Mark jobs as emailed
                    for job in todays_jobs:
                        if job.status == "qualified":
                            job.status = "emailed"
                            job.emailed_at = datetime.now(timezone.utc).isoformat()
                            db.upsert_job(job)
                else:
                    print("   ✗ Failed to send email")
            else:
                print("   (No qualified jobs to send)")

        else:
            print("\n⏭️ Phase 5: Notification (skipped --dry-run)")

        # Update run record
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        run.completed_at = end_time.isoformat()
        run.duration_seconds = duration
        run.discovered = stats["discovered"]
        run.extracted = stats["extracted"]
        run.quick_rejected = stats["quick_rejected"]
        run.scored = stats["scored"]
        run.qualified = stats["qualified"]
        run.resumes_generated = stats["resumes"]
        run.email_sent = not dry_run
        run.errors = json.dumps(errors) if errors else None

        db.update_run(run)

        print(f"\n✅ Run complete in {duration:.1f}s")
        print(f"   Discovered: {run.discovered}")
        print(f"   Extracted: {run.extracted}")
        print(f"   Qualified: {run.qualified}")
        print(f"   Resumes: {run.resumes_generated}")

    except Exception as e:
        errors.append(str(e))
        run.errors = json.dumps(errors)
        db.update_run(run)
        raise


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Run the async pipeline
    asyncio.run(run_pipeline(
        dry_run=args.dry_run,
        score_only=args.score_only,
        email_only=args.email_only,
        config_path=args.config,
    ))


if __name__ == "__main__":
    main()
