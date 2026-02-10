# Seedling — Project Instructions

> *"Find the good ones. Skip the garbage. Wake up to a plan."*

## Project Overview

Seedling is a local Python script that automates job hunting. It runs daily on a Mac Mini, discovering job listings, filtering out low-quality opportunities, generating tailored resumes, and emailing a curated digest.

**Key Distinction:** No auto-apply. No browser automation. Just discovery, filtering, and resume generation. You apply via browser extension.

## Architecture

```
Discovery (RSS + Web Search)
    ↓
Extraction (Shutter UV tool)
    ↓
Scoring (Kimi K2.5 via OpenRouter)
    ↓
Tailoring (HTML → PDF via Playwright)
    ↓
Upload (R2)
    ↓
Notify (Zephyr Worker digest email)
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Runtime | Python 3.12+ via UV |
| Database | SQLite (`~/.seedling/seedling.db`) |
| Discovery | `python-jobspy` (Indeed, Google Jobs scraping) |
| Extraction | Shutter (local UV tool - see `/Users/autumn/Documents/Projects/Shutter`) |
| Scoring | Kimi K2.5 via OpenRouter |
| Tailoring | Jinja2 → HTML → Playwright PDF |
| Storage | Cloudflare R2 |
| Email | Zephyr Worker (`grove-zephyr`) |
| Scheduling | macOS launchd |

## External Services

### Shutter (Extraction)
- **Location:** `/Users/autumn/Documents/Projects/Shutter`
- **Install:** Already installed via `uv tool install --editable /Users/autumn/Documents/Projects/Shutter`
- **Usage:** `shutter "URL" --query "what to extract" -m accurate -t 500`
- **Returns:** JSON with extracted content

### Zephyr Worker (Email)
- **Location:** `~/Documents/Projects/GroveEngine/workers/zephyr/`
- **Endpoint:** `POST https://grove-zephyr.<subdomain>.workers.dev/send`
- **Auth:** `Authorization: Bearer <ZEPHYR_API_KEY>`
- **Request:**
  ```json
  {
    "to": "autumnbrown23@pm.me",
    "subject": "Subject line",
    "html": "<html>...</html>",
    "text": "Plain text version"
  }
  ```

### Cloudflare R2
- **Account:** Configure via `secrets.json`
- **Bucket:** Create separate bucket for seedling resumes
- **Public URL:** Use `pub-<hash>.r2.dev` or custom domain

## Code Standards

### Python Style
- **Formatter:** Ruff (configured in pyproject.toml)
- **Type hints:** Required for all public functions
- **Async:** Use `async/await` for I/O operations (httpx, database)

### Project Structure
```
src/seedling/
├── __init__.py
├── main.py              # Entry point, orchestrator
├── config.py            # Load secrets.json + TOML config
├── db.py                # SQLite connection, schema, queries
│
├── discovery/
│   ├── __init__.py
│   └── jobspy.py        # Indeed/Google Jobs via python-jobspy
│
├── extraction/
│   ├── __init__.py
│   └── shutter.py       # Call shutter subprocess
│
├── scoring/
│   ├── __init__.py
│   ├── scorer.py        # Two-pass scoring logic
│   └── prompts.py       # LLM prompt templates
│
├── tailoring/
│   ├── __init__.py
│   ├── tailor.py        # Resume/cover letter generation
│   ├── renderer.py      # HTML → PDF via Playwright
│   └── uploader.py      # R2 upload
│
└── notify/
    ├── __init__.py
    └── digest.py        # Build digest HTML, send via Zephyr
```

### File Naming
- **Modules:** `snake_case.py`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Config keys:** `snake_case` (JSON), `kebab-case` (TOML)

### Git Commits
Follow conventional commits:
- `feat: Add new discovery source`
- `fix: Handle Shutter timeout gracefully`
- `chore: Update dependencies`
- `docs: Add scoring prompt documentation`

## Secrets Management

All secrets in `secrets.json` (gitignored):

```json
{
  "OPENROUTER_API_KEY": "...",
  "EXA_API_KEY": "...",
  "TAVILY_API_KEY": "...",
  "R2_ACCOUNT_ID": "...",
  "R2_ACCESS_KEY_ID": "...",
  "R2_SECRET_ACCESS_KEY": "...",
  "R2_BUCKET": "seedling-resumes",
  "R2_PUBLIC_URL": "",
  "ZEPHYR_URL": "https://grove-zephyr.<subdomain>.workers.dev/send",
  "ZEPHYR_API_KEY": "...",
  "SEEDLING_EMAIL": "autumnbrown23@pm.me"
}
```

**Loading secrets:**
```python
from seedling.config import load_secrets
secrets = load_secrets()
api_key = secrets["OPENROUTER_API_KEY"]
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=seedling

# Run specific test file
uv run pytest tests/test_scoring.py -v
```

## Development Workflow

1. **Create branch:** `git checkout -b feat/discovery-rss`
2. **Make changes:** Implement feature
3. **Run tests:** `uv run pytest`
4. **Commit:** `git commit -m "feat: Add Indeed RSS discovery"`
5. **Push:** `git push origin feat/discovery-rss`

## Available Skills

Claude Code Skills are available in `.claude/skills/`:

- `python-testing/` - pytest patterns
- `secrets-management/` - API key handling
- `database-management/` - SQLite patterns
- `git-workflows/` - Commit standards
- `code-quality/` - Code review

## Documentation

- **Spec:** `Seedling-spec.md` - Complete technical specification
- **Guides:** `AgentUsage/` - Extended reference documentation
- **README:** Project overview and quick start

---

*Last updated: February 9, 2026*

