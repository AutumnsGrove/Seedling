# Project Instructions - Agent Workflows

> **Note**: This is the main orchestrator file. For detailed guides, see `AgentUsage/README.md`

---

## Project Purpose
[Fill in: What this project does - 1-2 sentences]

## Tech Stack
[Fill in: Technologies, frameworks, and languages used]
- Language:
- Framework:
- Key Libraries:
- Package Manager:

## Architecture Notes
[Fill in: Key architectural decisions, patterns, or structure]

---

## Essential Instructions (Always Follow)

### Core Behavior
- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary for achieving your goal
- ALWAYS prefer editing existing files to creating new ones
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested

### Naming Conventions
- **Directories**: Use CamelCase (e.g., `VideoProcessor`, `AudioTools`, `DataAnalysis`)
- **Date-based paths**: Use skewer-case with YYYY-MM-DD (e.g., `logs-2025-01-15`, `backup-2025-12-31`)
- **No spaces or underscores** in directory names (except date-based paths)

### TODO Management
- **Always check `TODOS.md` first** when starting a task or session
- **Check `COMPLETED.md`** for context on past decisions and implementation details
- **Update immediately** when tasks are completed, added, or changed
- **Move completed tasks** from `TODOS.md` to `COMPLETED.md` to keep the TODO list focused
- Keep both lists current and accurate

### Git Workflow Essentials

**After completing major changes, you MUST commit your work.**

**Conventional Commits Format:**
```bash
<type>: <brief description>

<optional body>
```

**Common Types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

**Examples:**
```bash
feat: Add user authentication
fix: Correct timezone bug
docs: Update README
```

**For complete details:** See `AgentUsage/git_guide.md`

### Pull Requests

Use conventional commits format for PR titles:
```
feat: Add dark mode toggle
fix: Correct timezone bug
```

Write a brief description of what the PR does and why. No specific format required.

---

## When to Use Skills

**This project uses Claude Code Skills for specialized workflows. Invoke skills using the Skill tool when you encounter these situations:**

### Secrets & API Keys
- **When managing API keys or secrets** → Use skill: `secrets-management`
- **Before implementing secrets loading** → Use skill: `secrets-management`
- **When integrating external APIs** → Use skill: `api-integration`

### Cloudflare Development
- **When deploying to Cloudflare** → Use skill: `cloudflare-deployment`
- **Before using Cloudflare Workers, KV, R2, or D1** → Use skill: `cloudflare-deployment`
- **When setting up Cloudflare MCP server** → Use skill: `cloudflare-deployment`

### Package Management
- **When using UV package manager** → Use skill: `uv-package-manager`
- **Before creating pyproject.toml** → Use skill: `uv-package-manager`
- **When managing Python dependencies** → Use skill: `uv-package-manager`

### Authentication
- **When adding sign-in to a Grove app** → Use skill: `heartwood-auth`
- **When protecting admin routes** → Use skill: `heartwood-auth`
- **When validating user sessions** → Use skill: `heartwood-auth`
- **When integrating with Heartwood (GroveAuth)** → Use skill: `heartwood-auth`

### Version Control
- **Before making a git commit** → Use skill: `git-workflows`
- **Before creating a pull request** → Use skill: `git-workflows`
- **When initializing a new repo** → Use skill: `git-workflows`
- **For git workflow and branching** → Use skill: `git-workflows`
- **When setting up git hooks** → Use skill: `git-hooks`

### Project Organization
- **Triage GitHub project issues** → Use skill: `badger-triage`
- **Create issues from TODOs or brain dumps** → Use skill: `bee-collect`
- **Organize backlog and plan sprints** → Use skill: `badger-triage`
- **Explore codebase to understand patterns** → Use skill: `bloodhound-scout`
- **Design system architecture** → Use skill: `eagle-architect`
- **Implement multi-file features** → Use skill: `elephant-build`

### Code Quality & Testing
- **Decide what to test and write tests** → Use skill: `beaver-build`
- **Fix specific bugs precisely** → Use skill: `panther-strike`
- **Debug issues systematically** → Use skill: `lynx-repair`
- **Optimize code for performance** → Use skill: `deer-sense` / `fox-optimize`
- **Security audit and hardening** → Use skill: `raccoon-audit` / `hawk-survey` / `turtle-harden`

### Data & Database
- **Migrate data between systems** → Use skill: `bear-migrate`
- **Database operations and management** → Use skill: `druid`

### UI & Design
- **Design UI with glassmorphism and seasonal themes** → Use skill: `chameleon-adapt`
- **Design system components** → Use skill: `swan-design`

### Documentation & Knowledge
- **Document systems for team knowledge** → Use skill: `owl-archive`
- **Create user guides and onboarding** → Use skill: `robin-guide`

### Integration & Cleanup
- **Weave systems together** → Use skill: `spider-weave`
- **Clean up deprecated code** → Use skill: `vulture-sweep`

### Gathering Workflows
- **Gather architectural insights** → Use skill: `gathering-architecture`
- **Gather feature requirements** → Use skill: `gathering-feature`
- **Gather migration context** → Use skill: `gathering-migration`
- **Gather planning information** → Use skill: `gathering-planning`
- **Gather security context** → Use skill: `gathering-security`
- **Gather UI requirements** → Use skill: `gathering-ui`

### Database Management
- **When working with databases** → Use skill: `database-management`
- **Before implementing data persistence** → Use skill: `database-management`
- **For database.py template** → Use skill: `database-management`

### Research & Analysis
- **When researching technology decisions** → Use skill: `research-strategy`
- **When analyzing unfamiliar codebases** → Use skill: `research-strategy`
- **For systematic investigation** → Use skill: `research-strategy`

### Testing
- **When deciding what to test or reviewing test quality** → Use skill: `grove-testing`
- **Before writing Python tests** → Use skill: `python-testing`
- **Before writing JavaScript/TypeScript tests** → Use skill: `javascript-testing`
- **Before writing Go tests** → Use skill: `go-testing`
- **Before writing Rust tests** → Use skill: `rust-testing`

### Code Quality
- **When formatting or linting code** → Use skill: `code-quality`
- **Before major code changes** → Use skill: `code-quality`
- **For Black, Ruff, mypy usage** → Use skill: `code-quality`

### Project Setup & Infrastructure
- **When starting a new project** → Use skill: `project-scaffolding`
- **Setting up CI/CD pipelines** → Use skill: `cicd-automation`
- **When containerizing applications** → Use skill: `docker-workflows`

### Web Development
- **When building Svelte 5 applications** → Use skill: `svelte5-development`
- **For SvelteKit routing and forms** → Use skill: `svelte5-development`

### CLI Development
- **When building terminal interfaces** → Use skill: `rich-terminal-output`
- **For Rich library patterns** → Use skill: `rich-terminal-output`

### Grove UI Design
- **When creating or enhancing Grove pages** → Use skill: `grove-ui-design`
- **When adding decorative nature elements** → Use skill: `grove-ui-design`
- **When implementing glassmorphism effects** → Use skill: `grove-ui-design`
- **When working with seasonal themes** → Use skill: `grove-ui-design`
- **When building navigation patterns** → Use skill: `grove-ui-design`

### Grove Documentation
- **When writing help center articles** → Use skill: `grove-documentation`
- **When drafting specs or technical docs** → Use skill: `grove-documentation`
- **When writing user-facing text** → Use skill: `grove-documentation`
- **When writing onboarding, tooltips, or error messages** → Use skill: `grove-documentation`
- **When reviewing docs for voice consistency** → Use skill: `grove-documentation`

### Grove Specifications
- **When creating new technical specifications** → Use skill: `grove-spec-writing`
- **When reviewing specs for completeness** → Use skill: `grove-spec-writing`
- **When standardizing spec formatting** → Use skill: `grove-spec-writing`

### Museum Documentation
- **When writing documentation meant to be read by Wanderers** → Use skill: `museum-documentation`
- **When creating "how it works" content for knowledge base** → Use skill: `museum-documentation`
- **When documenting a codebase or system for curious visitors** → Use skill: `museum-documentation`
- **When writing elegant, narrative-driven technical explanations** → Use skill: `museum-documentation`

### Grove Naming
- **When naming a new service or feature** → Use skill: `walking-through-the-grove`
- **When finding a Grove-themed name** → Use skill: `walking-through-the-grove`

### Package Publishing
- **When publishing to npm** → Use skill: `npm-publish`
- **Before npm package releases** → Use skill: `npm-publish`

---

## Quick Reference

### How to Use Skills
Skills are invoked using the Skill tool. When a situation matches a skill trigger:
1. Invoke the skill by name (e.g., `skill: "secrets-management"`)
2. The skill will expand with detailed instructions
3. Follow the skill's guidance for the specific task

### Security Basics
- Store API keys in `secrets.json` (NEVER commit)
- Add `secrets.json` to `.gitignore` immediately
- Provide `secrets_template.json` for setup
- Use environment variables as fallbacks

### Available Skills Reference
| Skill | Purpose |
|-------|---------|
| `heartwood-auth` | Heartwood (GroveAuth) integration, sign-in, sessions |
| `secrets-management` | API keys, credentials, secrets.json |
| `api-integration` | External REST API integration |
| `database-management` | SQLite, database.py patterns |
| `git-workflows` | Commits, branching, conventional commits (via GW tool) |
| `git-hooks` | Pre-commit hooks setup |
| `uv-package-manager` | Python dependencies with UV |
| `grove-testing` | Testing philosophy, what/when to test |
| `python-testing` | pytest, fixtures, mocking |
| `javascript-testing` | Vitest/Jest testing |
| `go-testing` | Go testing patterns |
| `rust-testing` | Cargo test patterns |
| `code-quality` | Black, Ruff, mypy |
| `project-scaffolding` | New project setup |
| `cicd-automation` | GitHub Actions workflows |
| `docker-workflows` | Containerization |
| `cloudflare-deployment` | Workers, KV, R2, D1 |
| `svelte5-development` | Svelte 5 with runes |
| `rich-terminal-output` | Terminal UI with Rich |
| `grove-ui-design` | Glassmorphism, seasons, forests, warm UI |
| `grove-documentation` | Grove voice, help articles, user-facing text |
| `grove-spec-writing` | Technical specifications with Grove formatting |
| `museum-documentation` | Elegant, narrative documentation for Wanderers |
| `walking-through-the-grove` | Finding Grove-themed names for new services |
| `npm-publish` | npm package publishing workflow |
| `research-strategy` | Systematic research |
| **Project Organization** | |
| `badger-triage` | GitHub project board triage, issue sizing, prioritization |
| `bee-collect` | Create GitHub issues from TODOs, brain dumps |
| `bloodhound-scout` | Code exploration, pattern tracking, dependency mapping |
| `eagle-architect` | High-level system design, architecture planning |
| `elephant-build` | Multi-file feature implementation, coordinated changes |
| **Code Quality & Testing** | |
| `beaver-build` | Test strategy, what/how to test, building test suites |
| `panther-strike` | Precise bug fixes, targeted repairs |
| `lynx-repair` | Systematic debugging, issue diagnosis |
| `deer-sense` | Performance optimization, speed improvements |
| `fox-optimize` | Code optimization, efficiency gains |
| `raccoon-audit` | Security auditing, vulnerability assessment |
| `hawk-survey` | Security review, threat analysis |
| `turtle-harden` | Security hardening, defense in depth |
| **Data & Database** | |
| `bear-migrate` | Data migration, schema transformation |
| `druid` | Database operations, queries, D1 management |
| **UI & Design** | |
| `chameleon-adapt` | Glassmorphism, seasonal themes, Grove UI design |
| `swan-design` | Design system components, visual design |
| **Documentation** | |
| `owl-archive` | Documentation, knowledge management, team docs |
| `robin-guide` | User guides, onboarding, walkthroughs |
| **Integration & Cleanup** | |
| `spider-weave` | System integration, weaving components together |
| `vulture-sweep` | Cleanup, deprecated code removal, maintenance |
| **Gathering Workflows** | |
| `gathering-architecture` | Gather architectural insights, system context |
| `gathering-feature` | Gather feature requirements, user needs |
| `gathering-migration` | Gather migration context, data mapping |
| `gathering-planning` | Gather planning information, project context |
| `gathering-security` | Gather security context, threat model |
| `gathering-ui` | Gather UI requirements, design constraints |

---

## Code Style Guidelines

### Function & Variable Naming
- Use meaningful, descriptive names
- Keep functions small and focused on single responsibilities
- Add docstrings to functions and classes

### Error Handling
- Use try/except blocks gracefully
- Provide helpful error messages
- Never let errors fail silently

### File Organization
- Group related functionality into modules
- Use consistent import ordering:
  1. Standard library
  2. Third-party packages
  3. Local imports
- Keep configuration separate from logic

---

## Communication Style
- Be concise but thorough
- Explain reasoning for significant decisions
- Ask for clarification when requirements are ambiguous
- Proactively suggest improvements when appropriate

---

## Additional Resources

### Skills Documentation
Skills are the primary way to access specialized knowledge. Use the Skill tool to invoke them.
Skills are located in `.claude/skills/` and provide concise, actionable guidance.

### Extended Documentation
For in-depth reference beyond what skills provide, see:
**`AgentUsage/README.md`** - Master index of detailed documentation

---

## Grove Wrap (gw) Tool

This project uses **Grove Wrap (`gw`)** as the primary CLI tool for git operations, GitHub interactions, Cloudflare development, and more. The `gw` tool provides agent-safe defaults with safety tiers for all operations.

### Installation

```bash
cd tools/gw
uv sync
```

The `gw` command is now available. You can add an alias to your shell:
```bash
alias gw="uv run --project ~/path/to/tools/gw gw"
```

### Key Commands

| Command | What it does | Safety |
|---------|--------------|--------|
| `gw git status` | Enhanced git status | ✅ Always safe |
| `gw git commit --write -m "..."` | Commit changes | ⚠️ Needs `--write` |
| `gw git push --write` | Push to remote | ⚠️ Needs `--write` |
| `gw gh pr list` | List pull requests | ✅ Always safe |
| `gw gh pr create --write` | Create PR | ⚠️ Needs `--write` |
| `gw health` | Health check all components | ✅ Always safe |
| `gw deploy --write` | Deploy to Cloudflare | ⚠️ Needs `--write` |

### Safety System

The `--write` flag is required for any operation that modifies data:
- **READ operations** (status, list, view) - Always safe, no flag needed
- **WRITE operations** (commit, push, create) - Need `--write` flag
- **DANGEROUS operations** (force push, hard reset) - Need `--write --force`

### Git Workflows Integration

The `git-workflows` skill uses `gw` for all git and GitHub operations. This provides:
- Conventional commits validation
- Protected branch guards
- Audit logging for agent mode
- Consistent error handling

See `tools/gw/README.md` for complete documentation.

---

*Last updated: 2026-01-22*
*Model: Claude Opus 4.5*
