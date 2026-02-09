#!/usr/bin/env bash

# BaseProject Update/Sync Script
# Syncs AgentUsage folder, skills, and git hooks from the latest BaseProject version
# Handles migration from old ClaudeUsage folders

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Constants
BASEPROJECT_REPO="https://github.com/AutumnsGrove/BaseProject.git"
TEMP_DIR="/tmp/baseproject-update-$$"
BACKUP_DIR=".baseproject-backup-$(date +%Y%m%d-%H%M%S)"
SUMMARY_FILE="baseproject-update-summary.md"

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_section() {
    echo ""
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}$1${NC}"
    echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Cleanup function
cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        log_info "Cleaning up temporary files..."
        rm -rf "$TEMP_DIR"
    fi
}

trap cleanup EXIT

# Check if we're in a project directory
check_environment() {
    if [ ! -d ".git" ]; then
        log_warning "Not in a git repository. This is recommended but not required."
        read -p "Continue anyway? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_error "Aborted by user"
            exit 1
        fi
    fi
}

# Clone BaseProject to temp directory
clone_baseproject() {
    log_section "Fetching Latest BaseProject"

    log_info "Cloning BaseProject repository..."
    if git clone --depth 1 --branch main "$BASEPROJECT_REPO" "$TEMP_DIR" &>/dev/null; then
        log_success "Successfully cloned BaseProject"
    else
        log_error "Failed to clone BaseProject repository"
        exit 1
    fi
}

# Migrate old ClaudeUsage to AgentUsage
migrate_old_folders() {
    log_section "Checking for Old Folders"

    local migrated=false

    # Check for ClaudeUsage folder
    if [ -d "ClaudeUsage" ]; then
        log_warning "Found old 'ClaudeUsage' folder"

        # Create backup
        mkdir -p "$BACKUP_DIR"
        cp -r ClaudeUsage "$BACKUP_DIR/"
        log_success "Backed up ClaudeUsage to $BACKUP_DIR/"

        # If AgentUsage doesn't exist, just rename
        if [ ! -d "AgentUsage" ]; then
            mv ClaudeUsage AgentUsage
            log_success "Renamed ClaudeUsage → AgentUsage"
        else
            # Merge old ClaudeUsage into existing AgentUsage
            log_info "Merging ClaudeUsage into AgentUsage..."

            # Copy any custom files that don't exist in AgentUsage
            find ClaudeUsage -type f | while read -r file; do
                relative_path="${file#ClaudeUsage/}"
                if [ ! -f "AgentUsage/$relative_path" ]; then
                    mkdir -p "AgentUsage/$(dirname "$relative_path")"
                    cp "$file" "AgentUsage/$relative_path"
                    log_success "Migrated: $relative_path"
                fi
            done

            # Remove old ClaudeUsage folder
            rm -rf ClaudeUsage
            log_success "Removed old ClaudeUsage folder"
        fi

        migrated=true
    fi

    if [ "$migrated" = false ]; then
        log_info "No old folders found - you're up to date!"
    fi
}

# Create backup of existing AgentUsage
backup_existing() {
    log_section "Creating Backup"

    if [ -d "AgentUsage" ]; then
        mkdir -p "$BACKUP_DIR"
        cp -r AgentUsage "$BACKUP_DIR/"
        log_success "Backed up existing AgentUsage to $BACKUP_DIR/"
    else
        log_info "No existing AgentUsage folder to backup"
    fi
}

# Sync AgentUsage folder
sync_agent_usage() {
    log_section "Syncing AgentUsage Folder"

    local added=0
    local updated=0
    local unchanged=0

    # Create AgentUsage if it doesn't exist
    mkdir -p AgentUsage

    # Sync files from BaseProject
    while IFS= read -r -d '' file; do
        relative_path="${file#$TEMP_DIR/AgentUsage/}"
        target_file="AgentUsage/$relative_path"

        # Create directory if needed
        mkdir -p "$(dirname "$target_file")"

        # Check if file exists and compare
        if [ ! -f "$target_file" ]; then
            cp "$file" "$target_file"
            log_success "Added: $relative_path"
            ((added++))
        else
            # Compare files
            if ! cmp -s "$file" "$target_file"; then
                cp "$file" "$target_file"
                log_success "Updated: $relative_path"
                ((updated++))
            else
                ((unchanged++))
            fi
        fi
    done < <(find "$TEMP_DIR/AgentUsage" -type f -print0)

    echo ""
    log_info "Sync Summary:"
    log_success "  Added: $added files"
    log_success "  Updated: $updated files"
    log_info "  Unchanged: $unchanged files"
}

# Sync skills folder
sync_skills() {
    log_section "Syncing Claude Code Skills"

    local added=0
    local updated=0
    local unchanged=0

    # Create .claude/skills directory if it doesn't exist
    mkdir -p .claude/skills

    # Check if source skills exist
    if [ ! -d "$TEMP_DIR/.claude/skills" ]; then
        log_warning "No skills found in BaseProject"
        return
    fi

    # Sync skills from BaseProject
    while IFS= read -r -d '' file; do
        relative_path="${file#$TEMP_DIR/.claude/skills/}"
        target_file=".claude/skills/$relative_path"

        # Create directory if needed
        mkdir -p "$(dirname "$target_file")"

        # Check if file exists and compare
        if [ ! -f "$target_file" ]; then
            cp "$file" "$target_file"
            log_success "Added: $relative_path"
            ((added++))
        else
            # Compare files
            if ! cmp -s "$file" "$target_file"; then
                cp "$file" "$target_file"
                log_success "Updated: $relative_path"
                ((updated++))
            else
                ((unchanged++))
            fi
        fi
    done < <(find "$TEMP_DIR/.claude/skills" -type f -print0)

    echo ""
    log_info "Skills Sync Summary:"
    log_success "  Added: $added files"
    log_success "  Updated: $updated files"
    log_info "  Unchanged: $unchanged files"

    # List available skills
    echo ""
    log_info "Available skills:"
    for skill_dir in .claude/skills/*/; do
        if [ -d "$skill_dir" ]; then
            skill_name=$(basename "$skill_dir")
            echo "  • $skill_name"
        fi
    done
}

# Sync tools folder
sync_tools() {
    log_section "Syncing Tools"

    local added=0
    local updated=0
    local unchanged=0

    # Check if source tools exist
    if [ ! -d "$TEMP_DIR/tools" ]; then
        log_warning "No tools found in BaseProject"
        return
    fi

    # Create tools directory if it doesn't exist
    mkdir -p tools

    # Sync tools from BaseProject (excluding uv.lock which is per-project)
    while IFS= read -r -d '' file; do
        relative_path="${file#$TEMP_DIR/tools/}"

        # Skip lock files
        if [[ "$relative_path" == *.lock ]]; then
            continue
        fi

        target_file="tools/$relative_path"

        # Create directory if needed
        mkdir -p "$(dirname "$target_file")"

        # Check if file exists and compare
        if [ ! -f "$target_file" ]; then
            cp "$file" "$target_file"
            log_success "Added: tools/$relative_path"
            ((added++))
        else
            # Compare files
            if ! cmp -s "$file" "$target_file"; then
                cp "$file" "$target_file"
                log_success "Updated: tools/$relative_path"
                ((updated++))
            else
                ((unchanged++))
            fi
        fi
    done < <(find "$TEMP_DIR/tools" -type f -print0)

    echo ""
    log_info "Tools Sync Summary:"
    log_success "  Added: $added files"
    log_success "  Updated: $updated files"
    log_info "  Unchanged: $unchanged files"

    # Remind about installing
    if [ $added -gt 0 ] || [ $updated -gt 0 ]; then
        echo ""
        log_info "To install/update grove-find CLI:"
        echo -e "  ${YELLOW}uv tool install --editable tools/grove-find${NC}"
    fi
}

# Merge .gitignore entries
merge_gitignore() {
    log_section "Updating .gitignore"

    if [ ! -f ".gitignore" ]; then
        log_info "Creating new .gitignore"
        cp "$TEMP_DIR/.gitignore" .gitignore
        log_success "Created .gitignore"
        return
    fi

    # Backup existing .gitignore
    mkdir -p "$BACKUP_DIR"
    cp .gitignore "$BACKUP_DIR/"

    local added=0

    # Read entries from BaseProject's .gitignore
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" =~ ^# ]]; then
            continue
        fi

        # Check if entry already exists
        if ! grep -qF "$line" .gitignore; then
            echo "$line" >> .gitignore
            ((added++))
        fi
    done < "$TEMP_DIR/.gitignore"

    if [ $added -gt 0 ]; then
        log_success "Added $added new entries to .gitignore"
    else
        log_info ".gitignore is up to date"
    fi
}

# Update git hooks
update_git_hooks() {
    log_section "Git Hooks Update"

    if [ ! -d ".git" ]; then
        log_warning "Not a git repository, skipping hooks"
        return
    fi

    log_info "Git hooks have been updated in AgentUsage/pre_commit_hooks/"
    log_info "To install/update your hooks, run:"
    echo ""
    echo -e "${YELLOW}    ./AgentUsage/pre_commit_hooks/install_hooks.sh${NC}"
    echo ""

    read -p "Would you like to reinstall git hooks now? [y/N]: " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -x "AgentUsage/pre_commit_hooks/install_hooks.sh" ]; then
            ./AgentUsage/pre_commit_hooks/install_hooks.sh
            log_success "Git hooks updated"
        else
            log_error "Hook installer not found or not executable"
        fi
    else
        log_info "Skipped git hooks installation"
    fi
}

# Generate summary report
generate_summary() {
    log_section "Generating Update Report"

    cat > "$SUMMARY_FILE" << EOF
# BaseProject Update Summary

**Date:** $(date '+%Y-%m-%d %H:%M:%S')
**Updated From:** BaseProject main branch

## What Was Updated

### Claude Code Skills (Primary)
- Skills in \`.claude/skills/\` have been synced with the latest BaseProject version
- **Skills are the primary mechanism** for accessing specialized knowledge
- Use skills via the Skill tool (e.g., \`skill: "database-management"\`)

### AgentUsage Folder (Extended Reference)
- Extended documentation guides have been synced
- Git hooks in \`AgentUsage/pre_commit_hooks/\` have been updated
- Templates in \`AgentUsage/templates/\` have been refreshed

### Tools Folder (CLI Tools)
- \`tools/grove-find/\` - grove-find CLI search tool (Python/typer)
- To install: \`uv tool install --editable tools/grove-find\`

### .gitignore
- New entries from BaseProject have been merged
- Your existing entries have been preserved

## What Was NOT Changed

The following files were **preserved** and not modified:
- \`AGENT.md\` - Your project-specific instructions
- \`README.md\` - Your project documentation
- \`TODOS.md\` - Your task list
- \`secrets.json\` / \`secrets_template.json\` - Your API keys
- Language-specific files (pyproject.toml, package.json, etc.)
- Your source code and tests

## Backup Location

A backup of your previous setup has been saved to:
\`$BACKUP_DIR/\`

## Next Steps

1. Review the changes:
   \`\`\`bash
   git diff .claude/skills/ AgentUsage/ tools/
   \`\`\`

2. If you updated git hooks, test them:
   \`\`\`bash
   git add .
   git commit -m "test: verify hooks are working"
   \`\`\`

3. If everything looks good, commit the updates:
   \`\`\`bash
   git add .claude/skills/ AgentUsage/ tools/ .gitignore
   git commit -m "chore: sync skills, docs, and tools from BaseProject

   - Updated Claude Code Skills
   - Updated extended documentation
   - Updated CLI tools (grove-find)
   - Refreshed git hooks
   - Merged new .gitignore entries"
   \`\`\`

4. If you encounter issues, restore from backup:
   \`\`\`bash
   rm -rf AgentUsage
   cp -r $BACKUP_DIR/AgentUsage .
   \`\`\`

## Available Skills

Skills are invoked using the Skill tool when you encounter relevant situations:
- \`secrets-management\` - API keys, credentials
- \`database-management\` - SQLite, database.py patterns
- \`git-workflows\` - Commits, branching
- \`python-testing\` - pytest patterns
- \`docker-workflows\` - Containerization
- \`cicd-automation\` - GitHub Actions
- See \`.claude/skills/\` for the full list

## Extended Documentation

For in-depth reference beyond what skills provide:
- \`AgentUsage/README.md\` - Index of all guides with skill mapping
- \`AgentUsage/git_guide.md\` - Git workflow patterns
- \`AgentUsage/pre_commit_hooks/\` - Latest hook implementations

---

*For questions or issues, see: https://github.com/AutumnsGrove/BaseProject*
EOF

    log_success "Created $SUMMARY_FILE"
}

# Main execution
main() {
    clear

    echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║         BaseProject Update/Sync Tool                        ║${NC}"
    echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "This script will update your project with the latest documentation,"
    echo "skills, guides, and git hooks from BaseProject."
    echo ""
    echo -e "${YELLOW}What will be updated:${NC}"
    echo "  • .claude/skills/ folder (Claude Code Skills)"
    echo "  • AgentUsage/ folder (extended reference docs)"
    echo "  • tools/ folder (grove-find CLI search tool)"
    echo "  • .gitignore entries (merged, not replaced)"
    echo ""
    echo -e "${GREEN}What will NOT be changed:${NC}"
    echo "  • AGENT.md (your project instructions)"
    echo "  • README.md (your documentation)"
    echo "  • TODOS.md (your tasks)"
    echo "  • secrets.json / secrets_template.json"
    echo "  • Your source code and language configs"
    echo ""

    read -p "Continue with update? [y/N]: " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_error "Update cancelled by user"
        exit 0
    fi

    # Run update steps
    check_environment
    clone_baseproject
    migrate_old_folders
    backup_existing
    sync_skills
    sync_agent_usage
    sync_tools
    merge_gitignore
    update_git_hooks
    generate_summary

    # Final summary
    log_section "Update Complete!"

    echo -e "${GREEN}✓${NC} Skills folder has been synced with latest BaseProject"
    echo -e "${GREEN}✓${NC} AgentUsage folder has been synced with latest BaseProject"
    echo -e "${GREEN}✓${NC} Tools folder has been synced with latest BaseProject"
    echo -e "${GREEN}✓${NC} Backup saved to: $BACKUP_DIR/"
    echo -e "${GREEN}✓${NC} Update summary saved to: $SUMMARY_FILE"
    echo ""
    echo "Next steps:"
    echo "  1. Review changes: ${YELLOW}cat $SUMMARY_FILE${NC}"
    echo "  2. Check diffs: ${YELLOW}git diff .claude/skills/ AgentUsage/ tools/${NC}"
    echo "  3. Commit updates: ${YELLOW}git add . && git commit${NC}"
    echo ""
    echo -e "${BLUE}Happy coding! 🚀${NC}"
}

# Run main function
main
