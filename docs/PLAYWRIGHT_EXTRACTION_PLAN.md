# Seedling Playwright Extraction Plan

> **Objective:** Replace expensive/limited extraction APIs with local Playwright browser automation for robust, free job description extraction.

## Executive Summary

| Aspect | Current State | Target State |
|--------|---------------|--------------|
| **Extraction** | Shutter/Tavily (blocked) | Playwright + Stealth |
| **Cost** | $0 (Shutter) or $20+/mo (Tavily) | $0 (local) |
| **Success Rate** | ~20% (blocked) | ~60-80% (stealth) |
| **Daily Runs** | Limited by API | Unlimited |
| **Resources** | N/A | 1-2GB RAM per run |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DAILY PIPELINE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: Discovery         Phase 2: Extraction                 │
│  ┌─────────────────┐        ┌─────────────────────────────────┐ │
│  │ • RSS Feeds     │        │                                 │ │
│  │ • JSearch API   │──URL──▶│  Playwright Extraction Queue    │ │
│  │ • Company APIs  │        │  ├─ Apply stealth plugins       │ │
│  └─────────────────┘        │  ├─ Load page (wait for DOM)    │ │
│                             │  ├─ Extract structured data      │ │
│                             │  ├─ Block unnecessary resources │ │
│                             │  └─ Handle detection gracefully │ │
│                             └─────────────────────────────────┘ │
│                                      │                          │
│                                      ▼                          │
│                             ┌─────────────────────────────────┐ │
│                             │ Fallback Chain                  │ │
│                             │ 1. Shutter (free)               │ │
│                             │ 2. Skip (log for review)        │ │
│                             └─────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Current State

### What's Working
- **RSS Discovery:** Indeed RSS feeds return job titles, URLs, and snippets
- **JSearch Integration:** Skeleton exists, needs valid API key
- **Database:** Jobs tracked with status: discovered → extracted → scored → qualified

### What's Broken
- **Shutter:** Jina Reader and Tavily both hit bot protection on job sites
- **Tavily Extract:** Returns 422 errors or "Failed to fetch url"
- **Extraction Rate:** ~20% success on job site pages

## Proposed Solution: Playwright Extraction

### Components

#### 1. PlaywrightDiscovery Class
```python
class PlaywrightDiscovery:
    """Extraction using local Playwright with stealth evasion."""

    async def extract_batch(
        self,
        urls: list[str],
        max_concurrent: int = 2,
        timeout_ms: int = 30000,
    ) -> list[ExtractionResult]:
        """Extract multiple URLs with controlled concurrency."""
```

#### 2. Stealth Configuration
```python
STEALTH_CONFIG = {
    "navigator_webdriver": True,       # Mask webdriver flag
    "navigator_languages": ("en-US", "en"),
    "navigator_platform": "Win32",
    "navigator_user_agent": True,      # Patch UA headers
    "webgl_vendor": True,              # Mock WebGL
    "chrome_runtime": True,            # Hide Chrome APIs
}
```

#### 3. Resource Blocking
```python
RESOURCE_TYPES_BLOCKED = ["image", "stylesheet", "font", "media"]
```

#### 4. Site-Specific Selectors
```python
SITE_SELECTORS = {
    "indeed.com": {
        "description": ".jobsearch-jobDescriptionText",
        "title": ".jobsearch-JobInfo-headerTitle",
        "company": ".jobsearch-CompanyInfo-withLogo",
        "location": ".jobsearch-JobInfo-headerLocation",
        "salary": ".jobsearch-JobMetadataHeader-item",
    },
    "glassdoor.com": {
        "description": "[data-test='job-description-content']",
        "title": "[data-test='job-title']",
        "company": "[data-test='employer-name']",
    },
    "ziprecruiter.com": {
        "description": "[class*='JobDetail']",
        "title": "h1[class*='JobTitle']",
    },
    # Generic fallback
    None: {
        "description": "body",
        "title": "h1",
    }
}
```

#### 5. Result Structure
```python
@dataclass
class ExtractionResult:
    url: str
    success: bool
    title: str | None
    company: str | None
    location: str | None
    salary: str | None
    description: str
    error: str | None
    detection_flagged: bool = False
    response_time_ms: int = 0
```

### Extraction Flow

```
1. Load browser with stealth configuration
2. Navigate to URL with wait_until="domcontentloaded"
3. Wait for site-specific selector (10s timeout)
4. Check for bot detection (CAPTCHA, block page)
5. Extract data using site-specific selectors
6. Fallback to generic selectors if needed
7. Save result with metadata
8. Close page, recycle context every 10 URLs
9. Add random delay (1-3s) between extractions
```

### Detection Handling

| Signal | Action |
|--------|--------|
| CAPTCHA present | Skip, mark for manual review |
| "Access Denied" page | Skip, log URL |
| 404/500 error | Retry once, then skip |
| Timeout (30s) | Skip, log |
| Detection flagged | Rotate context, continue |

### Fallback Chain

```
Playwright Extraction
        │
        ├─ Success → Continue pipeline
        │
        ├─ Detection/Block
        │       │
        │       └─ Try Shutter (free, lightweight)
        │               │
        │               ├─ Success → Continue
        │               └─ Fail → Log to skipped_jobs table
        │
        └─ Complete failure → Log for manual review
```

## Resource Requirements

### Local Execution (Mac Mini)

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 2GB | 4GB |
| **CPU** | 1 core | 2 cores |
| **Disk** | 500MB | 1GB |
| **Duration** | 2-5 min | 1-3 min |
| **Concurrency** | 1 | 2 |

### Docker Configuration (if needed)

```yaml
services:
  seedling:
    image: seedling:latest
    shm_size: 2gb
    mem_limit: 4g
    environment:
      - PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
    volumes:
      - ./data:/app/data
```

### Browser Launch Args

```python
browser = await p.chromium.launch(
    headless=True,  # Run without GUI for efficiency
    args=[
        "--disable-dev-shm-usage",       # Avoid memory crashes in containers
        "--no-sandbox",                  # Non-root user requirement
        "--disable-setuid-sandbox",
        "--disable-gpu",                 # No GPU available
        "--disable-software-rasterizer",
        "--disable-extensions",
        "--disable-plugins",
        "--single-process",              # Consolidate Chromium processes
    ]
)
```

## Configuration

### Environment Variables

```bash
# Optional overrides
PLAYWRIGHT_HEADLESS=true        # Default: true
PLAYWRIGHT_CONCURRENCY=2        # Default: 2
PLAYWRIGHT_TIMEOUT_MS=30000     # Default: 30000
PLAYWRIGHT_STEALTH=true         # Default: true
PLAYWRIGHT_DELAY_MIN_MS=1000    # Default: 1000
PLAYWRIGHT_DELAY_MAX_MS=3000    # Default: 3000
```

### Secrets (no changes needed)

All existing secrets continue to work. No new API keys required.

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Extraction success rate | ≥70% | successful / total attempted |
| Average extraction time | <5s | Per URL |
| Daily extraction capacity | Unlimited | N/A |
| Fallback to Shutter | <20% | Shutter calls / total failures |
| Manual review needed | <5% | Skipped jobs requiring review |

## Implementation Phases

### Phase 1: Core Extraction (Priority)
- [ ] Create `PlaywrightExtractor` class with async support
- [ ] Add site-specific selectors for major job sites
- [ ] Implement stealth configuration
- [ ] Add resource blocking (images/fonts)
- [ ] Wire into main.py extraction phase
- [ ] Test on 50 job URLs

### Phase 2: Resilience
- [ ] Add detection handling (CAPTCHA, blocks)
- [ ] Implement fallback to Shutter
- [ ] Add context recycling (new context every N pages)
- [ ] Add retry logic with exponential backoff
- [ ] Implement rate limiting (delay between requests)

### Phase 3: Optimization
- [ ] Add concurrency control (semaphore)
- [ ] Implement page pooling
- [ ] Add memory monitoring
- [ ] Create extraction stats logging
- [ ] Implement URL prioritization

### Phase 4: Monitoring
- [ ] Track extraction success by site
- [ ] Log failed URLs for analysis
- [ ] Create dashboard of extraction rates
- [ ] Alert on unusual failure patterns
- [ ] Track resource usage over time

## Files to Modify

```
src/seedling/
├── extraction/
│   ├── playwright.py          # NEW: Main extraction module
│   └── __init__.py            # Update exports
├── main.py                    # Wire Playwright into extraction phase
└── config.py                  # Add Playwright config if needed

tests/
└── test_extraction.py         # Add Playwright tests

docs/
└── PLAYWRIGHT_EXTRACTION.md   # Usage documentation
```

## Estimated Success Rates by Site

| Site | Expected Success | Notes |
|------|------------------|-------|
| Company career pages | 85-95% | Easiest target |
| Indeed | 70-85% | Good public data |
| Glassdoor | 50-70% | Some login walls |
| ZipRecruiter | 50-70% | Moderate protection |
| Monster | 60-80% | Standard protection |

**Note:** LinkedIn is excluded entirely due to ban risk.

**Overall weighted average: ~65-75%**

## Future Enhancements

### v2.0: Proxy Rotation
```python
# Add residential proxy support for blocked sites
PROXY_POOL = [
    "http://user:pass@proxy1:port",
    "http://user:pass@proxy2:port,
]
```

### v2.1: Browser Pool
```python
# Pre-launch multiple browsers for parallel extraction
browser_pool = BrowserPool(size=4)
job = await browser_pool.acquire()
# ... extract ...
browser_pool.release(job)
```

### v2.2: Cloudflare Workers Integration
```python
# Deploy headless browser API to Cloudflare Workers
# Requires Wrangler + headless Chromium compilation
```

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sites block headless Chrome | High | Stealth plugins, headful fallback |
| Memory exhaustion | Medium | Context recycling, limits |
| Site structure changes | Medium | Selector versioning, logging |
| New anti-bot measures | Medium | Regular stealth updates |

## Rollout Plan

1. **Day 1:** Implement core extraction, test on 20 URLs
2. **Day 2:** Add resilience (retry, fallback), test on 100 URLs
3. **Day 3:** Wire into main pipeline, full dry-run
4. **Day 4:** Production run, monitor success rates
5. **Day 5+:** Iterate based on metrics

## Success Criteria

- [ ] ≥60% extraction success rate on first run
- [ ] No manual intervention needed for extraction
- [ ] Complete pipeline runs in <10 minutes
- [ ] Zero API costs for extraction
- [ ] Logs clearly show extraction status per URL

---

*Last updated: February 9, 2026*
