#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                            ║
# ║   ███████╗██╗  ██╗ █████╗ ██████╗ ███████╗██████╗                          ║
# ║   ██╔════╝██║  ██║██╔══██╗██╔══██╗██╔════╝██╔══██╗                         ║
# ║   ███████╗███████║███████║██████╔╝█████╗  ██║  ██║                         ║
# ║   ╚════██║██╔══██║██╔══██║██╔══██╗██╔══╝  ██║  ██║                         ║
# ║   ███████║██║  ██║██║  ██║██║  ██║███████╗██████╔╝                         ║
# ║   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═════╝                          ║
# ║   ███╗   ███╗ ██████╗ ███╗   ███╗███████╗███╗   ██╗████████╗███████╗      ║
# ║   ████╗ ████║██╔═══██╗████╗ ████║██╔════╝████╗  ██║╚══██╔══╝██╔════╝      ║
# ║   ██╔████╔██║██║   ██║██╔████╔██║█████╗  ██╔██╗ ██║   ██║   ███████╗      ║
# ║   ██║╚██╔╝██║██║   ██║██║╚██╔╝██║██╔══╝  ██║╚██╗██║   ██║   ╚════██║      ║
# ║   ██║ ╚═╝ ██║╚██████╔╝██║ ╚═╝ ██║███████╗██║ ╚████║   ██║   ███████║      ║
# ║   ╚═╝     ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝      ║
# ║                                                                            ║
# ║   Update Script for SharedMoments v2                                       ║
# ║   https://github.com/tech-kev/SharedMoments                                ║
# ║                                                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

# ── Verbose Mode ───────────────────────────────────────────────────────────
VERBOSE=false
for arg in "$@"; do case $arg in -v|--verbose) VERBOSE=true ;; esac; done

# ── Colors & Formatting ──────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ── Helper Functions ─────────────────────────────────────────────────────────

info()    { echo -e "  ${BLUE}ℹ${NC}  $1"; }
success() { echo -e "  ${GREEN}✔${NC}  $1"; }
warn()    { echo -e "  ${YELLOW}⚠${NC}  $1"; }
fail()    { echo -e "  ${RED}✖${NC}  $1"; exit 1; }

TOTAL_STEPS=5

progress_bar() {
    local current=$1
    local total=$2
    local width=47
    local filled=$(( (current * width) / total ))
    local empty=$(( width - filled ))
    local pct=$(( (current * 100) / total ))
    local bar=""
    for (( i=0; i<filled; i++ )); do bar+="█"; done
    for (( i=0; i<empty; i++ )); do bar+="░"; done
    echo -e "  ${GREEN}${bar}${NC}  ${BOLD}${pct}%${NC}"
}

step() {
    local label=$1
    local current=${2:-0}
    echo ""
    echo -e "  ${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  ${BOLD}${CYAN}${label}${NC}"
    if [[ $current -gt 0 ]]; then
        progress_bar "$current" "$TOTAL_STEPS"
    fi
    echo -e "  ${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

spinner() {
    local pid=$1
    local msg=$2
    local chars='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while kill -0 "$pid" 2>/dev/null; do
        for (( i=0; i<${#chars}; i++ )); do
            printf "\r  ${CYAN}%s${NC}  %s" "${chars:$i:1}" "$msg"
            sleep 0.1
        done
    done
    wait "$pid"
    local exit_code=$?
    printf "\r"
    return $exit_code
}

run_task() {
    local msg="$1"
    shift
    if $VERBOSE; then
        info "$msg"
        "$@" 2>&1 | while IFS= read -r line; do
            echo -e "  ${DIM}│${NC} $line"
        done
    else
        "$@" &>/dev/null &
        spinner $! "$msg"
    fi
}

# ── Pre-flight Checks ────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
    fail "This script must be run as root. Try: ${BOLD}sudo bash update.sh${NC}"
fi

# Detect install directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/run.py" ]]; then
    INSTALL_DIR="$SCRIPT_DIR"
elif [[ -f "/opt/sharedmoments/run.py" ]]; then
    INSTALL_DIR="/opt/sharedmoments"
else
    fail "Could not find SharedMoments installation. Run this script from the install directory."
fi

clear
echo ""
echo -e "  ${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${CYAN}║${NC}                                                          ${CYAN}║${NC}"
echo -e "  ${CYAN}║${NC}   ${BOLD}SharedMoments v2 — Update${NC}                              ${CYAN}║${NC}"
echo -e "  ${CYAN}║${NC}                                                          ${CYAN}║${NC}"
echo -e "  ${CYAN}║${NC}   ${DIM}Updating your installation to the latest version${NC}       ${CYAN}║${NC}"
echo -e "  ${CYAN}║${NC}                                                          ${CYAN}║${NC}"
echo -e "  ${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
if $VERBOSE; then
    info "Verbose mode enabled — showing command output"
    echo ""
fi

info "Install directory: ${BOLD}${INSTALL_DIR}${NC}"

# Check if it's a git repo
if [[ ! -d "$INSTALL_DIR/.git" ]]; then
    fail "Not a git repository. Cannot update without git history."
fi

# Show current version
cd "$INSTALL_DIR"
GIT_REPO_URL="https://github.com/tech-kev/SharedMoments.git"

# Fix ownership warning (root runs script, repo owned by sharedmoments)
git config --global --add safe.directory "$INSTALL_DIR" 2>/dev/null || true

# Ensure remote origin exists
if ! git remote get-url origin &>/dev/null; then
    info "No git remote found — adding origin..."
    git remote add origin "$GIT_REPO_URL"
fi

# Ensure we're on a real branch (not detached HEAD from git init)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
if [[ "$CURRENT_BRANCH" == "HEAD" || "$CURRENT_BRANCH" == "unknown" || "$CURRENT_BRANCH" == "master" ]]; then
    CURRENT_BRANCH="main"
    info "Switching to branch ${BOLD}${CURRENT_BRANCH}${NC}..."
    git fetch --quiet origin 2>/dev/null || true
    git checkout -B "$CURRENT_BRANCH" "origin/$CURRENT_BRANCH" --quiet 2>/dev/null || git checkout -B "$CURRENT_BRANCH" --quiet 2>/dev/null || true
fi

CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
info "Current version: ${BOLD}${CURRENT_COMMIT}${NC} (branch: ${CURRENT_BRANCH})"

# Check for remote updates
info "Checking for updates..."
git fetch --quiet origin 2>/dev/null || warn "Could not fetch from remote"

LOCAL=$(git rev-parse HEAD 2>/dev/null)
REMOTE=$(git rev-parse "origin/${CURRENT_BRANCH}" 2>/dev/null || echo "")

if [[ -n "$REMOTE" && "$LOCAL" == "$REMOTE" ]]; then
    echo ""
    success "Already up to date! Nothing to do."
    echo ""
    exit 0
fi

if [[ -n "$REMOTE" ]]; then
    COMMITS_BEHIND=$(git rev-list --count HEAD.."origin/${CURRENT_BRANCH}" 2>/dev/null || echo "?")
    info "Updates available: ${BOLD}${COMMITS_BEHIND} new commit(s)${NC}"
fi

echo ""
echo -ne "  ${BOLD}Proceed with update? [Y/n]${NC}: "
read -r confirm < /dev/tty
if [[ "${confirm,,}" == "n" ]]; then
    info "Update cancelled."
    exit 0
fi

# ── Step 1: Backup ──────────────────────────────────────────────────────────

step "Step 1/5 — Creating backup" 1
info "Saving configuration and database..."

BACKUP_DIR="$INSTALL_DIR/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup .env
if [[ -f "$INSTALL_DIR/.env" ]]; then
    cp "$INSTALL_DIR/.env" "$BACKUP_DIR/.env"
    success "Configuration backed up"
fi

# Backup database (SQLite only)
if [[ -f "$INSTALL_DIR/app/database/sharedmoments.db" ]]; then
    cp "$INSTALL_DIR/app/database/sharedmoments.db" "$BACKUP_DIR/sharedmoments.db"
    DB_SIZE=$(du -sh "$BACKUP_DIR/sharedmoments.db" | cut -f1)
    success "Database backed up (${DB_SIZE})"
else
    info "No SQLite database found (using external DB or first run)"
fi

success "Backup saved to: ${DIM}${BACKUP_DIR}${NC}"

# ── Step 2: Stop Service ─────────────────────────────────────────────────────

step "Step 2/5 — Stopping service" 2

if systemctl is-active --quiet sharedmoments 2>/dev/null; then
    systemctl stop sharedmoments
    success "Service stopped"
else
    info "Service was not running"
fi

# ── Step 3: Pull Latest Code ─────────────────────────────────────────────────

step "Step 3/5 — Pulling latest code" 3
info "Fetching latest changes from remote..."

# Discard any local changes to tracked files (config is in .env, not tracked)
if [[ -n "$(git status --porcelain 2>/dev/null)" ]]; then
    warn "Local changes to source files detected — overwriting with latest version"
    warn "Your configuration (.env) is safe and will not be touched"
    git checkout -- . 2>/dev/null || true
    git clean -fd 2>/dev/null || true
fi

git fetch --quiet origin "$CURRENT_BRANCH" 2>/dev/null || fail "Could not fetch from remote"
git reset --hard "origin/$CURRENT_BRANCH" --quiet 2>/dev/null || fail "Git reset failed"

NEW_COMMIT=$(git rev-parse --short HEAD)
success "Code updated: ${BOLD}${CURRENT_COMMIT}${NC} → ${BOLD}${NEW_COMMIT}${NC}"

# ── Step 4: Update Dependencies ──────────────────────────────────────────────

step "Step 4/5 — Updating dependencies" 4
info "Updating pip and installing new/changed packages — this may take a moment..."

_task_update_pip() {
    "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    "$INSTALL_DIR/.venv/bin/pip" install gunicorn
}
run_task "Updating Python dependencies..." _task_update_pip
success "Dependencies updated"

# ── Step 5: Database Migrations & Restart ─────────────────────────────────────

step "Step 5/5 — Running migrations & restarting" 5
info "Applying database migrations and restarting service..."

_task_run_migrations() {
    cd "$INSTALL_DIR"
    sudo -u sharedmoments "$INSTALL_DIR/.venv/bin/python" -c "
from app import app
from app.models import Base, engine
from app.db_queries import init_db, ensure_reminder_permissions, ensure_edition_settings, ensure_list_type_edition_column
from app.translation import load_translation_in_cache, migrateTranslations
from app.notifications import _ensure_vapid_keys

Base.metadata.create_all(engine)
init_db()
ensure_reminder_permissions()
ensure_edition_settings()
ensure_list_type_edition_column()
migrateTranslations()
load_translation_in_cache()
_ensure_vapid_keys()
"
}
run_task "Running database migrations..." _task_run_migrations
success "Migrations complete"

# Fix ownership
chown -R sharedmoments:sharedmoments "$INSTALL_DIR"

# Reload systemd in case service file changed
systemctl daemon-reload

# Start service
systemctl start sharedmoments

sleep 2
if systemctl is-active --quiet sharedmoments; then
    success "Service restarted successfully"
else
    warn "Service may not have started. Check: ${BOLD}journalctl -u sharedmoments -n 50${NC}"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo ""
echo -e "  ${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}   ${BOLD}${GREEN}✔  Update complete!${NC}                                    ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "  ${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}What happened:${NC}"
echo -e "    ${DIM}1.${NC} Backup created in ${DIM}${BACKUP_DIR}${NC}"
echo -e "    ${DIM}2.${NC} Code updated from ${BOLD}${CURRENT_COMMIT}${NC} to ${BOLD}${NEW_COMMIT}${NC}"
echo -e "    ${DIM}3.${NC} Dependencies updated"
echo -e "    ${DIM}4.${NC} Database migrations applied"
echo -e "    ${DIM}5.${NC} Service restarted"
echo ""
echo -e "  ${BOLD}If something went wrong:${NC}"
echo -e "    ${DIM}Restore .env:${NC}     cp ${BACKUP_DIR}/.env ${INSTALL_DIR}/.env"
echo -e "    ${DIM}Restore DB:${NC}       cp ${BACKUP_DIR}/sharedmoments.db ${INSTALL_DIR}/app/database/"
echo -e "    ${DIM}Rollback code:${NC}    cd ${INSTALL_DIR} && git checkout ${CURRENT_COMMIT}"
echo -e "    ${DIM}Service logs:${NC}     journalctl -u sharedmoments -n 50"
echo ""
echo -e "  ${DIM}────────────────────────────────────────────────────────${NC}"
echo -e "  ${DIM}SharedMoments v2 • https://github.com/tech-kev/SharedMoments${NC}"
echo ""
