# 🌱 Seedling v2 — Local Job Scout & Resume Tailor

> *"Find the good ones. Skip the garbage. Wake up to a plan."*

A local Python script that runs on your Mac Mini every morning, finds relevant job listings, filters out the garbage, generates tailored resumes, and emails you a curated digest. You wake up, open the email, and apply to the good ones with your browser extension.

**Repository:** `AutumnsGrove/Seedling`
**Runtime:** Python 3.12+ via UV, runs locally on Mac Mini
**Schedule:** Daily cron (launchd on macOS)
**Last Updated:** February 8, 2026

---

## What It Does

Every morning, Seedling:

1. **Discovers** job listings via Indeed RSS feeds and web search
2. **Extracts** the actual job details from each listing using Shutter (local UV tool)
3. **Scores** each job using Kimi K2.5 to filter out garbage (wrong experience level, misleading titles, bad pay)
4. **Tailors** a resume PDF for each qualified job (and cover letter for tech roles that ask for one)
5. **Uploads** the tailored documents to R2 with public/signed URLs
6. **Emails** you a beautiful digest via Zephyr with scored jobs, direct apply links, and resume download links

That's it. No auto-apply. No browser automation. No Durable Objects. A cron job and a script.

---

## Why This Architecture

The previous design used Cloudflare Workers, Durable Objects, Browser Rendering, Stagehand, KV, D1, circuit breakers, and eight separate Workers. That was over-engineered for the actual problem:

**The actual problem:** Sorting through garbage job listings is demoralizing and time-consuming. Entry-level jobs that want 5 years of experience, "cybersecurity analyst" roles that are really help desk, serving jobs that pay $2.13 with no mention of tips. The hard part is finding the good ones, not clicking "apply."

**The solution:** Automate the finding and filtering. Leave the applying to a human with a browser extension.

**Why local:**
- Shutter works as a UV tool right now, not as a deployed worker (API key hardening needed)
- Local Playwright is more reliable than Cloudflare Browser Rendering (fully supported, no session limits)
- A Mac Mini running 24/7 is a perfectly good server
- No deployment pipeline needed — edit and run
- SQLite instead of D1 — same SQL, zero network latency, zero cost
- Faster iteration — change a scoring prompt, run it again immediately

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Discovery   │────▶│  Extraction  │────▶│   Scoring    │
│              │     │              │     │              │
│ Indeed RSS   │     │ Shutter      │     │ Kimi K2.5    │
│ Web Search   │     │ (UV tool)    │     │ (OpenRouter) │
│ (Playwright) │     │              │     │              │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                                 ▼
                    ┌─────────────┐     ┌──────────────┐
                    │   Notify    │◀────│   Tailor     │
                    │             │     │              │
                    │ Zephyr      │     │ Kimi K2.5    │
                    │ (Worker)    │     │ HTML → PDF   │
                    │             │     │ Upload to R2 │
                    └─────────────┘     └──────────────┘
```

### Components

| Component | Tech | Purpose |
|-----------|------|---------|
| **Discovery** | `feedparser` + `httpx` | Parse Indeed RSS, run web searches via Exa/Tavily API |
| **Extraction** | Shutter (local UV tool) | Fetch each listing URL → structured job data |
| **Scoring** | Kimi K2.5 via OpenRouter | Two-pass: quick reject → detailed scoring |
| **Tailoring** | Kimi K2.5 + Playwright | Generate tailored content → inject into HTML template → `page.pdf()` |
| **Storage** | SQLite (local) + R2 (remote) | Jobs/history in SQLite, resume PDFs in R2 |
| **Notification** | Zephyr Worker (existing) | Send digest email via Resend |
| **Scheduling** | macOS launchd | Run daily at 7:00 AM ET |

---

## Phase 1: Discovery

### Indeed RSS Feeds (Primary)

Indeed exposes RSS feeds for job searches with zero authentication:

```
https://www.indeed.com/rss?q={query}&l={location}&sort=date
```

Parameters:
- `q` — search query (URL encoded)
- `l` — location
- `sort=date` — newest first
- `radius` — miles from location
- `jt` — job type (fulltime, parttime, contract)
- `fromage` — max age in days

**Tech feeds:**
```python
TECH_FEEDS = [
    "https://www.indeed.com/rss?q=cybersecurity+analyst&l=Atlanta%2C+GA&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=cybersecurity+analyst&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=security+engineer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=systems+engineer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=platform+engineer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=full+stack+developer&l=Atlanta%2C+GA&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=full+stack+developer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=web+developer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=devops+engineer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=site+reliability+engineer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=infrastructure+engineer&l=remote&sort=date&fromage=3",
]

SERVING_FEEDS = [
    "https://www.indeed.com/rss?q=server+restaurant&l=Atlanta%2C+GA&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=bartender&l=Atlanta%2C+GA&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=host+restaurant&l=Atlanta%2C+GA&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=food+runner&l=Smyrna%2C+GA&sort=date&fromage=3",
]
```

Each RSS item gives us: title, company (in title), location, link, brief description, publish date. Parse with `feedparser`.

### Web Search (Secondary — covers LinkedIn, Glassdoor, Dice, etc.)

For platforms without RSS, use Exa or Tavily API to search:

```python
WEB_SEARCHES = [
    "cybersecurity analyst entry level remote job posting site:linkedin.com/jobs",
    "security engineer junior remote job posting site:dice.com",
    "full stack developer entry level Atlanta site:glassdoor.com/job-listing",
    "server bartender host Atlanta site:poached.com",
    "restaurant server Atlanta site:culinaryagents.com",
]
```

Web search returns URLs + snippets. Good enough for deduplication and deciding what's worth extracting.

### Playwright (Backup)

For anything that needs a real browser — platforms that block simple HTTP requests, pages that render client-side, or search results that need scrolling/pagination. Playwright runs locally, fully supported, no flakiness.

Use sparingly. RSS + web search should cover 90%+ of discovery.

### Deduplication

Before extraction, check SQLite for existing URL hashes. Skip anything already seen. Simple SHA-256 of the canonical URL.

---

## Phase 2: Extraction (Shutter)

For each new job URL discovered, call Shutter locally:

```bash
uvx shutter extract "https://www.indeed.com/viewjob?jk=abc123" \
    --query "Extract: job title, company, location (remote/onsite/hybrid), salary range, full description, required qualifications, preferred qualifications, posting date, application method" \
    --model accurate \
    --max-tokens 500
```

Shutter returns clean structured text. Parse this into a structured dict/dataclass.

**Why Shutter:**
- Handles the full page fetch + content extraction in one call
- ~200 tokens output from a 20k token page
- Prompt injection defense (Canary check)
- Works right now as a UV tool, no deployment needed

**Fallback:** If Shutter fails on a URL (timeout, blocked), try a simple `httpx` fetch + BeautifulSoup extraction, or Playwright for JS-rendered pages.

**Batch processing:** Process URLs concurrently with `asyncio` + `asyncio.Semaphore` (limit 5-10 concurrent). Each extraction is independent.

---

## Phase 3: Scoring

Two-pass scoring using Kimi K2.5 via OpenRouter (`moonshotai/kimi-k2.5`).

### Pass 1: Quick Reject

Cheap, fast prompt that catches obvious mismatches. Run on all extracted jobs.

```
Given this job listing, answer YES or NO for each:
1. Does it require 3+ years of professional experience?
2. Is it a senior/staff/principal/director/manager level role?
3. Is the listed salary below $40k (tech) or below minimum wage (serving)?
4. Is the actual role significantly different from the title (e.g., "Security Analyst" that's really Help Desk)?
5. Does it require a specific certification I don't have (CISSP, CISM, etc.)?

If any answer is YES, this job is REJECTED with a one-line reason.
If all answers are NO, this job PASSES to detailed scoring.
```

This eliminates 50-70% of listings for pennies.

### Pass 2: Detailed Scoring

For jobs that pass the quick filter, a more nuanced evaluation:

**Tech scoring dimensions:**
- **Skill match** (0–100): How well do my skills align? (TypeScript, Cloudflare Workers, Python, systems programming, WebAssembly, MCP, full-stack web dev, security tools)
- **Growth potential** (0–100): Will this teach me things I want to learn? (Rust, low-level systems, infrastructure)
- **Logistics** (0–100): Remote? Atlanta? Relocation support?
- **Compensation signal** (0–100): Salary range when visible, company reputation as proxy
- **Application ease** (low/medium/high): Quick Apply? Long form? Portfolio required?

**Serving scoring dimensions:**
- **Location** (0–100): Distance from Smyrna/Atlanta area
- **Schedule** (0–100): Flexible? Evenings/weekends? Part-time OK?
- **Pay signal** (0–100): Base + tips potential, mentioned compensation
- **Vibe** (0–100): Does the listing suggest a decent workplace?

**Output:** Composite score (0–100), category tag, 2-sentence "why this matched" summary.

**Threshold:** Tech ≥ 60, Serving ≥ 50 (serving is more urgent, cast a wider net).

### Candidate Profile (provided to scoring LLM)

```
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
```

---

## Phase 4: Tailoring

For each job that passes scoring:

### Tech Resume

1. Load base resume content (structured JSON — sections, bullets, skills)
2. Send to Kimi K2.5 with the job description: "Reorder and emphasize the following resume content to best match this job. Adjust the professional summary. Front-load matching skills. Reorder experience bullets by relevance. Do NOT fabricate experience. Do NOT remove the Grove project or capstone. Output as structured JSON."
3. Inject the tailored JSON into the HTML resume template
4. Render HTML → PDF via Playwright's `page.pdf()` (local, fast, reliable)
5. Upload PDF to R2 with a signed URL (or public URL with unguessable path)

### Tech Cover Letter (only when the listing explicitly requests one)

1. Generate via Kimi K2.5: 3 paragraphs max, specific to the job, references most relevant Grove work
2. Render HTML → PDF → R2
3. Flag in the digest that this job wanted a cover letter

### Serving Resume

1. Base serving resume is already strong (Publix food service, Food Handler's Permit, open availability)
2. Only tweak: adjust the 2-sentence professional summary based on role type (host/server/bartender)
3. Render HTML → PDF → R2

No cover letters for serving. Ever.

### HTML → PDF Pipeline

Both resumes use the same pipeline:
1. HTML template with CSS (beautiful, clean, ATS-friendly)
2. Template variables (`{{summary}}`, `{{skills}}`, `{{experience}}`, etc.)
3. Playwright opens the HTML, calls `page.pdf()` with A4/Letter sizing
4. Output: clean PDF, no weird formatting, full control over every pixel

The HTML templates are the ones you've already been building. They live in the repo.

---

## Phase 5: Notification (Zephyr Digest)

After all phases complete, send a digest email via the existing Zephyr Worker.

### Calling Zephyr from Python

Zephyr is a Cloudflare Worker that accepts POST requests and sends emails via Resend. From Python:

```python
import httpx

async def send_digest(html_content: str, subject: str):
    await httpx.post(
        "https://zephyr.your-domain.workers.dev/send",  # or workers.dev URL
        json={
            "to": "autumnbrown23@pm.me",
            "subject": subject,
            "html": html_content,
        },
        headers={"Authorization": "Bearer YOUR_ZEPHYR_KEY"},
    )
```

### Digest Content

**Subject line:** "🌱 Seedling: 8 matches found — 3 tech, 5 serving | Feb 9"

**Sections:**

1. **Greeting** — Rotating: "Your garden grew 8 new opportunities today 🌱"

2. **Top Tech Matches** — Ranked by score. Each entry:
   - Job title + company + location
   - Score (e.g., "87/100") + category tag
   - 2-sentence "why this matched" from the scorer
   - **[Apply →]** direct link to the listing
   - **[Resume]** link to the tailored resume PDF in R2
   - **[Cover Letter]** link (only if one was generated)

3. **Top Serving Matches** — Same format, simpler (no cover letter links)

4. **Rejected Summary** — "Filtered out 47 listings: 23 required 5+ years, 12 were actually help desk, 8 below pay threshold, 4 required CISSP"
   - This is important — it shows the tool is working and saving you time

5. **Stats** — Total discovered, extracted, scored, qualified. Running totals this week.

6. **Quick Actions** — If there's a review queue or settings to adjust

### Email Styling

React Email via Zephyr, or just well-structured HTML. The email should look good in Apple Mail and ProtonMail (your client). Dark-mode friendly. Clean, not cluttered.

---

## Data Model (SQLite)

One file: `~/.seedling/seedling.db`

### `jobs` table

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,                  -- nanoid
    platform TEXT NOT NULL,               -- indeed, linkedin, glassdoor, dice, poached, culinary_agents
    url TEXT NOT NULL,
    url_hash TEXT UNIQUE NOT NULL,         -- SHA-256 for dedup
    title TEXT,
    company TEXT,
    location TEXT,
    remote BOOLEAN DEFAULT FALSE,
    salary_min INTEGER,
    salary_max INTEGER,
    salary_text TEXT,                      -- raw string from listing
    description TEXT,                      -- full text from Shutter
    requirements TEXT,                     -- JSON array
    preferred TEXT,                        -- JSON array
    category TEXT,                         -- tech-cyber, tech-systems, tech-fullstack, tech-devops, serving
    match_score INTEGER,                   -- 0-100 composite
    score_breakdown TEXT,                  -- JSON per-dimension
    score_summary TEXT,                    -- 2-sentence "why this matched"
    quick_reject_reason TEXT,             -- if rejected in pass 1
    status TEXT DEFAULT 'discovered',      -- discovered, extracted, qualified, rejected, emailed
    resume_r2_url TEXT,                    -- public/signed URL to tailored resume
    cover_letter_r2_url TEXT,             -- public/signed URL to cover letter (tech only, optional)
    cover_letter_requested BOOLEAN DEFAULT FALSE,  -- did the listing ask for one?
    shutter_pi_detected BOOLEAN DEFAULT FALSE,
    discovered_at TEXT DEFAULT (datetime('now')),
    extracted_at TEXT,
    scored_at TEXT,
    emailed_at TEXT
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_score ON jobs(match_score DESC);
CREATE INDEX idx_jobs_date ON jobs(discovered_at DESC);
CREATE INDEX idx_jobs_category ON jobs(category);
```

### `runs` table

```sql
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    discovered INTEGER DEFAULT 0,
    extracted INTEGER DEFAULT 0,
    quick_rejected INTEGER DEFAULT 0,
    scored INTEGER DEFAULT 0,
    qualified INTEGER DEFAULT 0,
    resumes_generated INTEGER DEFAULT 0,
    email_sent BOOLEAN DEFAULT FALSE,
    errors TEXT,                           -- JSON array of error messages
    duration_seconds REAL
);
```

That's it. Two tables. No migrations framework needed — just `CREATE TABLE IF NOT EXISTS`.

---

## R2 Storage

Tailored resumes and cover letters uploaded to R2 for email links.

```
seedling-resumes/
├── tech/
│   ├── {job_id}-resume.pdf
│   └── {job_id}-cover-letter.pdf
└── serving/
    └── {job_id}-resume.pdf
```

**Access:** Public bucket with unguessable paths (nanoid in the job ID provides entropy), or signed URLs via the R2 API. Public is simpler — the URLs are only shared in your private email.

**Upload from Python:** Use `boto3` with R2's S3-compatible API, or `httpx` with R2's REST API.

```python
import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="https://{account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
)

s3.upload_file(
    "output/abc123-resume.pdf",
    "seedling-resumes",
    "tech/abc123-resume.pdf",
    ExtraArgs={"ContentType": "application/pdf"},
)
```

---

## Configuration

All config in a single TOML file: `~/.seedling/config.toml`

```toml
[general]
email = "autumnbrown23@pm.me"
db_path = "~/.seedling/seedling.db"
output_dir = "~/.seedling/output"  # local PDF staging before R2 upload
log_level = "INFO"

[discovery]
indeed_rss_enabled = true
web_search_enabled = true
playwright_enabled = false  # backup, off by default
max_age_days = 3  # only jobs posted in last 3 days

[discovery.indeed]
feeds = [
    # tech - remote
    "https://www.indeed.com/rss?q=cybersecurity+analyst&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=security+engineer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=systems+engineer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=platform+engineer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=full+stack+developer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=web+developer&l=remote&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=devops+engineer&l=remote&sort=date&fromage=3",
    # tech - Atlanta
    "https://www.indeed.com/rss?q=cybersecurity+analyst&l=Atlanta%2C+GA&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=full+stack+developer&l=Atlanta%2C+GA&sort=date&fromage=3",
    # serving - Atlanta
    "https://www.indeed.com/rss?q=server+restaurant&l=Atlanta%2C+GA&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=bartender&l=Atlanta%2C+GA&sort=date&fromage=3",
    "https://www.indeed.com/rss?q=host+restaurant&l=Atlanta%2C+GA&sort=date&fromage=3",
]

[discovery.web_search]
provider = "exa"  # or "tavily"
queries = [
    "cybersecurity analyst entry level remote job posting site:linkedin.com/jobs",
    "security engineer junior remote site:dice.com",
    "server bartender Atlanta site:poached.com",
]

[scoring]
tech_threshold = 60
serving_threshold = 50
model = "moonshotai/kimi-k2.5"
provider = "openrouter"

[tailoring]
model = "moonshotai/kimi-k2.5"
provider = "openrouter"
tech_template = "templates/tech-resume.html"
serving_template = "templates/serving-resume.html"
cover_letter_template = "templates/cover-letter.html"
generate_cover_letters = "when_requested"  # "always", "never", "when_requested"

[r2]
account_id = "..."
bucket = "seedling-resumes"
access_key_id = "..."
secret_access_key = "..."
public_url_base = "https://pub-{hash}.r2.dev"  # or custom domain

[zephyr]
url = "https://zephyr.your-workers.dev/send"
api_key = "..."

[secrets]
openrouter_api_key = "..."
exa_api_key = "..."       # or tavily
```

Secrets can also come from environment variables: `SEEDLING_OPENROUTER_KEY`, etc.

---

## Project Structure

```
seedling/
├── pyproject.toml              # UV project config
├── uv.lock
├── README.md
├── config.example.toml
│
├── src/
│   └── seedling/
│       ├── __init__.py
│       ├── main.py             # Entry point — orchestrates the pipeline
│       ├── config.py           # Load + validate TOML config
│       ├── db.py               # SQLite connection, schema init, queries
│       │
│       ├── discovery/
│       │   ├── __init__.py
│       │   ├── rss.py          # Indeed RSS feed parsing
│       │   ├── web_search.py   # Exa/Tavily search
│       │   └── playwright.py   # Backup browser-based discovery
│       │
│       ├── extraction/
│       │   ├── __init__.py
│       │   └── shutter.py      # Call Shutter as UV subprocess
│       │
│       ├── scoring/
│       │   ├── __init__.py
│       │   ├── scorer.py       # Two-pass scoring logic
│       │   └── prompts.py      # LLM prompt templates
│       │
│       ├── tailoring/
│       │   ├── __init__.py
│       │   ├── tailor.py       # Resume + cover letter generation
│       │   ├── renderer.py     # HTML template → PDF via Playwright
│       │   └── uploader.py     # R2 upload
│       │
│       └── notify/
│           ├── __init__.py
│           └── digest.py       # Build digest HTML, send via Zephyr
│
├── templates/
│   ├── tech-resume.html        # HTML resume template (tech)
│   ├── serving-resume.html     # HTML resume template (serving)
│   ├── cover-letter.html       # HTML cover letter template
│   └── digest-email.html       # Digest email template
│
└── tests/
    ├── test_rss.py
    ├── test_scoring.py
    └── test_renderer.py
```

---

## Dependencies (pyproject.toml)

```toml
[project]
name = "seedling"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "feedparser",           # RSS parsing
    "httpx[http2]",         # HTTP client (async)
    "openai",               # OpenRouter uses OpenAI-compatible API
    "boto3",                # R2 upload (S3-compatible)
    "playwright",           # HTML → PDF rendering + backup scraping
    "beautifulsoup4",       # HTML parsing fallback
    "jinja2",               # HTML template rendering
    "tomli",                # TOML config parsing (stdlib in 3.11+, but explicit)
    "nanoid",               # Job IDs
    "rich",                 # Pretty console output during runs
]

[project.scripts]
seedling = "seedling.main:main"
```

---

## Running

```bash
# First time setup
uv sync
uv run playwright install chromium

# Manual run
uv run seedling

# Or with UV script shortcut
uv run seedling --dry-run        # discover + extract + score, but don't email
uv run seedling --score-only     # re-score already extracted jobs
uv run seedling --email-only     # re-send last digest
```

### macOS launchd (daily schedule)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>place.grove.seedling</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/autumn/.local/bin/uv</string>
        <string>run</string>
        <string>--project</string>
        <string>/Users/autumn/Code/Seedling</string>
        <string>seedling</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>7</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/autumn/.seedling/logs/seedling.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/autumn/.seedling/logs/seedling.error.log</string>
    <key>WorkingDirectory</key>
    <string>/Users/autumn/Code/Seedling</string>
</dict>
</plist>
```

Install: `cp place.grove.seedling.plist ~/Library/LaunchAgents/ && launchctl load ~/Library/LaunchAgents/place.grove.seedling.plist`

---

## Phased Build Plan

### Phase 1: Discovery + Database (Day 1)
- [ ] Init UV project with deps
- [ ] SQLite schema + `db.py`
- [ ] Indeed RSS parser (`feedparser` → parse → dedup → insert)
- [ ] Test: run RSS feeds, see jobs in SQLite
- [ ] TOML config loader

### Phase 2: Extraction (Day 1–2)
- [ ] Shutter integration (subprocess call to `uvx shutter extract`)
- [ ] Parse Shutter output into structured data
- [ ] Update SQLite with extracted fields
- [ ] Fallback: `httpx` + BeautifulSoup for simple pages
- [ ] Test: extract 10 Indeed listings, verify data quality

### Phase 3: Scoring (Day 2)
- [ ] OpenRouter client (OpenAI-compatible SDK)
- [ ] Quick reject prompt + logic
- [ ] Detailed scoring prompt + parsing
- [ ] Test: score extracted jobs, check that garbage gets filtered

### Phase 4: Digest Email (Day 2–3)
- [ ] Jinja2 email template
- [ ] Digest builder (query SQLite for today's qualified jobs)
- [ ] Zephyr integration (POST to Worker)
- [ ] Test: send yourself a real digest

**🎯 MVP DONE at this point.** You have a script that finds jobs, filters garbage, and emails you the good ones every morning. Everything below is enhancement.

### Phase 5: Resume Tailoring (Day 3–4)
- [ ] Base resume content as structured JSON
- [ ] Tailoring prompt (reorder, emphasize, adjust summary)
- [ ] HTML template + Jinja2 rendering
- [ ] Playwright PDF generation
- [ ] R2 upload + URL generation
- [ ] Add resume links to digest email

### Phase 6: Web Search Discovery (Day 4)
- [ ] Exa or Tavily integration
- [ ] Search query configuration
- [ ] URL extraction from search results
- [ ] Wire into existing extraction → scoring pipeline

### Phase 7: Cover Letters (Day 4–5)
- [ ] Detection: does the listing request a cover letter?
- [ ] Generation prompt
- [ ] HTML template → PDF → R2
- [ ] Add cover letter links to digest

### Phase 8: Polish
- [ ] Rich console output during runs
- [ ] Launchd plist + auto-scheduling
- [ ] Error handling + retry logic
- [ ] `--dry-run`, `--score-only`, `--email-only` flags
- [ ] Playwright backup discovery (if needed)

---

## Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| OpenRouter (Kimi K2.5) — scoring + tailoring | ~$3–8 |
| R2 storage (resume PDFs) | $0 (free tier) |
| Resend (via Zephyr) | $0 (free tier) |
| Exa or Tavily API (web search) | $0–5 (free tiers generous) |
| Mac Mini electricity | ~$3 |

**Total: ~$6–16/month.** Possibly less. The free tiers cover almost everything.

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Runtime | Python via UV (local) | Shutter is UV Python, simpler stack, faster iteration |
| Discovery (primary) | Indeed RSS feeds | Free, no auth, structured XML, reliable |
| Discovery (secondary) | Web search (Exa/Tavily) | Covers LinkedIn, Glassdoor, Dice, niche boards |
| Discovery (backup) | Playwright (local) | For JS-rendered or blocked pages |
| Extraction | Shutter (local UV tool) | Works now, cheap, PI defense, structured output |
| Scoring model | Kimi K2.5 via OpenRouter | Sonnet-quality, fraction of the cost |
| Tailoring model | Kimi K2.5 via OpenRouter | Same model, batch with scoring |
| Resume format | HTML → PDF via Playwright | Full CSS control, beautiful output, local + reliable |
| Database | SQLite (local) | Zero cost, zero latency, zero deployment |
| Resume storage | Cloudflare R2 | S3-compatible, free tier, public URLs for email links |
| Email delivery | Zephyr Worker (existing) | Already built, Resend integration, React Email |
| Auto-apply | **No** | Browser extension handles this, too complex and risky to automate |
| Cover letters | Only when listing explicitly asks | Most don't need them, especially serving |
| Scheduling | macOS launchd | Native, reliable, no extra daemon |
| Serving resume | Existing PDF base, light summary tweaks | Publix experience + Food Handler's Permit is already strong |
| Tech resume | Needs content update (add TS, Cloudflare, Grove) | Pre-req before building HTML template |

---

*Last updated: February 8, 2026*
