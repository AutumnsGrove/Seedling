"""Main entry point for Seedling.

Orchestrates the complete pipeline: discover → extract → score → tailor → notify.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from nanoid import generate

from seedling.config import load_secrets
from seedling.db import Database, Job, Run, get_database


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


async def run_pipeline(
    dry_run: bool = False,
    score_only: bool = False,
    email_only: bool = False,
) -> None:
    """Run the complete Seedling pipeline.

    Args:
        dry_run: If True, skip email sending.
        score_only: If True, only score already extracted jobs.
        email_only: If True, only send the digest email.
    """
    start_time = datetime.now()
    run_id = generate(size=12)

    print(f"🌱 Seedling v0.1.0 - {start_time.strftime('%Y-%m-%d %H:%M')}")
    print(f"   Run ID: {run_id}")
    print()

    # Load secrets
    try:
        secrets = load_secrets()
        print(f"✓ Loaded secrets for {secrets['SEEDLING_EMAIL']}")
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
        print("\nPlease create secrets.json from secrets_template.json")
        sys.exit(1)

    # Initialize database
    db = get_database()
    print(f"✓ Database initialized at {db.db_path}")

    # Create run record
    run = Run(id=run_id, started_at=start_time.isoformat())
    db.create_run(run)
    errors: list[str] = []

    try:
        # Phase 1: Discovery (unless score_only or email_only)
        if not score_only and not email_only:
            print("\n📡 Phase 1: Discovery")
            print("   (This phase discovers new job listings)")
            # TODO: Import and run discovery
            # from seedling.discovery import discover_jobs
            # jobs = await discover_jobs()
            # for job in jobs:
            #     db.upsert_job(job)
            print("   [Discovery module not yet implemented]")

        # Phase 2: Extraction (unless email_only)
        if not email_only:
            print("\n🔍 Phase 2: Extraction")
            print("   (This phase extracts job details using Shutter)")
            # TODO: Import and run extraction
            # from seedling.extraction import extract_job_details
            # jobs = db.get_jobs_by_status("discovered")
            # for job in jobs:
            #     extracted = await extract_job_details(job)
            #     db.upsert_job(extracted)
            print("   [Extraction module not yet implemented]")

        # Phase 3: Scoring (unless email_only)
        if not email_only:
            print("\n📊 Phase 3: Scoring")
            print("   (This phase scores jobs using Kimi K2.5)")
            # TODO: Import and run scoring
            # from seedling.scoring import score_job
            # jobs = db.get_jobs_by_status("extracted")
            # for job in jobs:
            #     scored = await score_job(job)
            #     db.upsert_job(scored)
            print("   [Scoring module not yet implemented]")

        # Phase 4: Tailoring (unless score_only or email_only)
        if not score_only and not email_only:
            print("\n📝 Phase 4: Tailoring")
            print("   (This phase generates tailored resumes)")
            # TODO: Import and run tailoring
            # from seedling.tailoring import tailor_resume
            # jobs = db.get_qualified_jobs()
            # for job in jobs:
            #     tailored = await tailor_resume(job)
            #     db.upsert_job(tailored)
            print("   [Tailoring module not yet implemented]")

        # Phase 5: Notification (unless dry_run)
        if not dry_run:
            print("\n📧 Phase 5: Notification")
            print("   (This phase sends the digest email)")
            # TODO: Import and run notification
            # from seedling.notify import send_digest
            # jobs = db.get_todays_jobs()
            # await send_digest(jobs, secrets)
            print("   [Notification module not yet implemented]")
        else:
            print("\n⏭️ Phase 5: Notification (skipped --dry-run)")

        # Update run record
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        stats = db.get_stats()
        run.completed_at = end_time.isoformat()
        run.duration_seconds = duration
        run.discovered = stats.get("total", 0)
        run.extracted = stats.get("extracted", 0)
        run.qualified = stats.get("qualified", 0)
        run.email_sent = not dry_run
        run.errors = json.dumps(errors) if errors else None

        db.update_run(run)

        print(f"\n✅ Run complete in {duration:.1f}s")
        print(f"   Discovered: {run.discovered}")
        print(f"   Extracted: {run.extracted}")
        print(f"   Qualified: {run.qualified}")

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
    ))


if __name__ == "__main__":
    main()
