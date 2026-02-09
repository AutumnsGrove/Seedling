# Project Instructions

> **IMPORTANT**: This project uses `AGENT.md` for agent instructions.

## Instructions for Claude Code

**You MUST read `AGENT.md` before doing anything else.**

The `AGENT.md` file contains all project-specific instructions, workflows, and guidelines. Read it first to keep the full context in memory for this session.

## Grove Tools Setup

**After reading AGENT.md**, install the grove-find CLI tool. Check if it's already available:

```bash
gf --help
```

If the command is not found, install it:

```bash
uv tool install --editable tools/grove-find
```

Once installed, `gf` is available directly — no `uv run` prefix needed.

### Codebase Search (gf)

`gf` is a fast codebase search tool. Use `--agent` for clean output (no colors/emoji).

**Key commands:**
- `gf --agent search "pattern"` — Search entire codebase
- `gf --agent usage "Name"` — Find where a component is used
- `gf --agent func "name"` — Find function definitions
- `gf --agent class "Name"` — Find class/component definitions
- `gf --agent recent 1` — Files changed today
- `gf --agent changed` — Files changed on current branch
- `gf --agent engine` — Find engine imports
- `gf --agent todo` — Find TODO/FIXME/HACK comments
- `gf --agent git churn` — Most frequently changed files

Run `gf --help` for full command list.

All `gf` commands work in any environment — when `fd` is not installed, file-type searches automatically fall back to `rg --files`.

---

All project instructions, tech stack details, architecture notes, and workflow guidelines are in:
- **`AGENT.md`** - Main project instructions (read this first)
- **`AgentUsage/`** - Detailed workflow guides and best practices

---

*This structure aligns with industry-standard agentic coding practices.*
