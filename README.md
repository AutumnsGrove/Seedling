# Seedling — Local Job Scout & Resume Tailor

> *"Find the good ones. Skip the garbage. Wake up to a plan."*

A local Python script that runs on your Mac Mini every morning, finds relevant job listings, filters out the garbage, generates tailored resumes, and emails you a curated digest.

**Repository:** `AutumnsGrove/Seedling`
**Runtime:** Python 3.12+ via UV, runs locally on Mac Mini
**Schedule:** Daily cron (launchd on macOS)

---

## What It Does

Every morning, Seedling:

1. **Discovers** job listings via Indeed RSS feeds and web search
2. **Extracts** the actual job details from each listing using [Shutter](https://github.com/AutumnsGrove/Shutter) (local UV tool)
3. **Scores** each job using Kimi K2.5 to filter out garbage
4. **Tailors** a resume PDF for each qualified job
5. **Uploads** the tailored documents to R2 with public/signed URLs
6. **Emails** you a beautiful digest via Zephyr with scored jobs and resume links

---

## Quick Start

```bash
# Install dependencies
uv sync
uv run playwright install chromium

# Run Seedling
uv run seedling

# Dry run (discover + extract + score, don't email)
uv run seedling --dry-run
```

---

## Project Structure

```
seedling/
├── pyproject.toml           # UV project config
├── uv.lock
├── README.md
├── secrets_template.json    # API key template
├── secrets.json             # Your API keys (gitignored)
│
├── src/
│   └── seedling/
│       ├── __init__.py
│       ├── main.py          # Entry point
│       ├── config.py        # TOML config loader
│       ├── db.py            # SQLite database
│       │
│       ├── discovery/       # Job discovery (RSS, web search)
│       ├── extraction/      # Shutter integration
│       ├── scoring/         # AI job scoring
│       ├── tailoring/       # Resume generation
│       └── notify/          # Zephyr digest email
│
├── templates/               # HTML templates
│   ├── tech-resume.html
│   ├── serving-resume.html
│   ├── cover-letter.html
│   └── digest-email.html
│
└── tests/                   # Unit tests
```

---

## Configuration

All configuration is managed via `secrets.json`:

| Key | Description |
|-----|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key for Kimi K2.5 |
| `EXA_API_KEY` | Exa API key for web search |
| `TAVILY_API_KEY` | Tavily API key (fallback) |
| `R2_ACCOUNT_ID` | Cloudflare R2 account ID |
| `R2_ACCESS_KEY_ID` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | R2 secret key |
| `R2_BUCKET` | R2 bucket name (e.g., `seedling-resumes`) |
| `ZEPHYR_URL` | Zephyr Worker URL |
| `ZEPHYR_API_KEY` | Zephyr API key |
| `SEEDLING_EMAIL` | Your email address |

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  Discovery   │────▶│  Extraction  │────▶│   Scoring    │
│              │     │              │     │              │
│ Indeed RSS   │     │ Shutter      │     │ Kimi K2.5    │
│ Web Search   │     │ (UV tool)    │     │ (OpenRouter) │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                                 ▼
                    ┌─────────────┐     ┌──────────────┐
                    │   Notify    │◀────│   Tailor     │
                    │             │     │              │
                    │ Zephyr      │     │ HTML → PDF   │
                    │ (Worker)    │     │ R2 upload    │
                    └─────────────┘     └──────────────┘
```

---

## Tech Stack

- **Runtime:** Python 3.12+ via UV
- **Database:** SQLite (`~/.seedling/seedling.db`)
- **Discovery:** feedparser, httpx, Exa/Tavily API
- **Extraction:** [Shutter](https://github.com/AutumnsGrove/Shutter) (local UV tool)
- **Scoring/Tailoring:** Kimi K2.5 via OpenRouter
- **PDF Generation:** Playwright (local)
- **Storage:** Cloudflare R2
- **Email:** Zephyr Worker (Resend)
- **Scheduling:** macOS launchd

---

## Commands

```bash
uv run seedling          # Full run: discover → extract → score → tailor → email
uv run seedling --dry-run    # Discover + extract + score only (no email)
uv run seedling --score-only # Re-score already extracted jobs
uv run seedling --email-only # Re-send last digest
```

---

## Development

See [AGENT.md](AGENT.md) for complete project instructions.

For extended documentation, see [AgentUsage/](AgentUsage/) directory.

---

*Last updated: February 9, 2026*
