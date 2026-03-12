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
# ║   Uninstall Script for SharedMoments v2                                    ║
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

TOTAL_STEPS=4

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

# ── Pre-flight Checks ────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
    fail "This script must be run as root. Try: ${BOLD}sudo bash uninstall.sh${NC}"
fi

# Detect install directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/run.py" ]]; then
    INSTALL_DIR="$SCRIPT_DIR"
elif [[ -f "/opt/sharedmoments/run.py" ]]; then
    INSTALL_DIR="/opt/sharedmoments"
else
    fail "Could not find SharedMoments installation."
fi

clear
echo ""
echo -e "  ${RED}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${RED}║${NC}                                                          ${RED}║${NC}"
echo -e "  ${RED}║${NC}   ${BOLD}SharedMoments v2 — Uninstall${NC}                           ${RED}║${NC}"
echo -e "  ${RED}║${NC}                                                          ${RED}║${NC}"
echo -e "  ${RED}║${NC}   ${DIM}This will remove SharedMoments from your system${NC}        ${RED}║${NC}"
echo -e "  ${RED}║${NC}                                                          ${RED}║${NC}"
echo -e "  ${RED}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

info "Install directory: ${BOLD}${INSTALL_DIR}${NC}"

# Show what will be removed
echo ""
echo -e "  ${BOLD}The following will be removed:${NC}"
echo -e "    ${RED}•${NC} Systemd service ${DIM}(sharedmoments.service)${NC}"
echo -e "    ${RED}•${NC} System user ${DIM}(sharedmoments)${NC}"

# Check for user data
HAS_DB=false
HAS_UPLOADS=false
UPLOAD_SIZE="0"
DB_SIZE="0"

if [[ -f "$INSTALL_DIR/app/database/sharedmoments.db" ]]; then
    HAS_DB=true
    DB_SIZE=$(du -sh "$INSTALL_DIR/app/database/sharedmoments.db" | cut -f1)
fi

if [[ -d "$INSTALL_DIR/app/uploads" ]] && [[ -n "$(ls -A "$INSTALL_DIR/app/uploads/images" 2>/dev/null)" || -n "$(ls -A "$INSTALL_DIR/app/uploads/videos" 2>/dev/null)" ]]; then
    HAS_UPLOADS=true
    UPLOAD_SIZE=$(du -sh "$INSTALL_DIR/app/uploads" 2>/dev/null | cut -f1)
fi

echo ""

if $HAS_DB || $HAS_UPLOADS; then
    echo -e "  ${YELLOW}${BOLD}User data detected:${NC}"
    if $HAS_DB; then
        echo -e "    ${YELLOW}•${NC} Database: ${BOLD}${DB_SIZE}${NC} ${DIM}(${INSTALL_DIR}/app/database/)${NC}"
    fi
    if $HAS_UPLOADS; then
        echo -e "    ${YELLOW}•${NC} Uploads:  ${BOLD}${UPLOAD_SIZE}${NC} ${DIM}(${INSTALL_DIR}/app/uploads/)${NC}"
    fi
    echo ""
fi

# Ask about data export
EXPORT_DATA=false
if $HAS_DB || $HAS_UPLOADS; then
    echo -ne "  ${BOLD}Create a backup of your data before uninstalling? [Y/n]${NC}: "
    read -r backup_confirm < /dev/tty
    if [[ "${backup_confirm,,}" != "n" ]]; then
        EXPORT_DATA=true
    fi
fi

# Final confirmation
echo ""
echo -e "  ${RED}${BOLD}⚠  WARNING: This action cannot be undone!${NC}"
echo -ne "  ${BOLD}Type '${RED}UNINSTALL${NC}${BOLD}' to confirm: ${NC}"
read -r confirm < /dev/tty
if [[ "$confirm" != "UNINSTALL" ]]; then
    info "Uninstall cancelled."
    exit 0
fi

# ── Step 1: Backup Data ──────────────────────────────────────────────────────

if $EXPORT_DATA; then
    step "Step 1/4 — Backing up data" 1

    BACKUP_DIR="/tmp/sharedmoments-backup-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    if $HAS_DB; then
        cp "$INSTALL_DIR/app/database/sharedmoments.db" "$BACKUP_DIR/"
        success "Database backed up"
    fi

    if $HAS_UPLOADS; then
        cp -r "$INSTALL_DIR/app/uploads" "$BACKUP_DIR/uploads"
        success "Uploads backed up"
    fi

    if [[ -f "$INSTALL_DIR/.env" ]]; then
        cp "$INSTALL_DIR/.env" "$BACKUP_DIR/.env"
        success "Configuration backed up"
    fi

    success "Backup saved to: ${BOLD}${BACKUP_DIR}${NC}"
else
    step "Step 1/4 — Skipping backup" 1
    info "No backup requested"
fi

# ── Step 2: Stop & Remove Service ────────────────────────────────────────────

step "Step 2/4 — Removing systemd service" 2

if systemctl is-active --quiet sharedmoments 2>/dev/null; then
    systemctl stop sharedmoments
    success "Service stopped"
else
    info "Service was not running"
fi

if systemctl is-enabled --quiet sharedmoments 2>/dev/null; then
    systemctl disable --quiet sharedmoments
    success "Service disabled"
fi

if [[ -f /etc/systemd/system/sharedmoments.service ]]; then
    rm /etc/systemd/system/sharedmoments.service
    systemctl daemon-reload
    success "Service file removed"
else
    info "No service file found"
fi

# ── Step 3: Remove Installation Directory ────────────────────────────────────

step "Step 3/4 — Removing application files" 3

if [[ -d "$INSTALL_DIR" ]]; then
    TOTAL_SIZE=$(du -sh "$INSTALL_DIR" 2>/dev/null | cut -f1)
    rm -rf "$INSTALL_DIR"
    success "Removed ${INSTALL_DIR} (${TOTAL_SIZE})"
else
    info "Directory already removed"
fi

# ── Step 4: Remove System User ───────────────────────────────────────────────

step "Step 4/4 — Removing system user" 4

if id -u sharedmoments &>/dev/null; then
    userdel sharedmoments 2>/dev/null || true
    success "System user 'sharedmoments' removed"
else
    info "System user was already removed"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo ""
echo -e "  ${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}   ${BOLD}${GREEN}✔  Uninstall complete!${NC}                                 ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "  ${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}What was removed:${NC}"
echo -e "    ${DIM}•${NC} Systemd service"
echo -e "    ${DIM}•${NC} Application files (${INSTALL_DIR})"
echo -e "    ${DIM}•${NC} System user (sharedmoments)"
echo ""

if $EXPORT_DATA; then
    echo -e "  ${BOLD}Your backup is saved at:${NC}"
    echo -e "    ${CYAN}➜${NC}  ${BACKUP_DIR}"
    echo ""
    echo -e "  ${DIM}Remember to move this backup to a safe location.${NC}"
    echo -e "  ${DIM}It will be deleted on next reboot (/tmp).${NC}"
    echo ""
fi

echo -e "  ${DIM}System packages (Python, ffmpeg, git) were NOT removed.${NC}"
echo -e "  ${DIM}Remove them manually if no longer needed.${NC}"
echo ""
echo -e "  ${DIM}────────────────────────────────────────────────────────${NC}"
echo -e "  ${DIM}Thank you for using SharedMoments!${NC}"
echo ""
