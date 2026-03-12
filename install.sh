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
# ║   One-Click Installer for SharedMoments v2                                 ║
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

TOTAL_STEPS=6

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
    echo -e "  ${GREEN}${bar}${NC}  ${BOLD}${pct}%%${NC}"
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

ask() {
    local prompt=$1
    local default=$2
    local var_name=$3
    if [[ -n "$default" ]]; then
        echo -ne "  ${BOLD}${prompt}${NC} ${DIM}[${default}]${NC}: "
    else
        echo -ne "  ${BOLD}${prompt}${NC}: "
    fi
    read -r input < /dev/tty
    eval "$var_name=\"${input:-$default}\""
}

ask_secret() {
    local prompt=$1
    local var_name=$2
    echo -ne "  ${BOLD}${prompt}${NC}: "
    read -rs input < /dev/tty
    echo ""
    eval "$var_name=\"$input\""
}

ask_choice() {
    local prompt=$1
    local options=$2
    local default=$3
    local var_name=$4
    echo -e "  ${BOLD}${prompt}${NC}"
    IFS='|' read -ra opts <<< "$options"
    for i in "${!opts[@]}"; do
        local num=$((i+1))
        if [[ "$num" == "$default" ]]; then
            echo -e "    ${GREEN}${num})${NC} ${opts[$i]} ${DIM}(default)${NC}"
        else
            echo -e "    ${DIM}${num})${NC} ${opts[$i]}"
        fi
    done
    echo -ne "  ${BOLD}Choose [1-${#opts[@]}]${NC} ${DIM}[${default}]${NC}: "
    read -r choice < /dev/tty
    choice=${choice:-$default}
    eval "$var_name=\"${opts[$((choice-1))]}\""
}

# ── Pre-flight Checks ────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
    fail "This script must be run as root. Try: ${BOLD}sudo bash install.sh${NC}"
fi

clear
echo ""
echo -e "  ${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${CYAN}║${NC}                                                          ${CYAN}║${NC}"
echo -e "  ${CYAN}║${NC}   ${BOLD}SharedMoments v2 — Installer${NC}                           ${CYAN}║${NC}"
echo -e "  ${CYAN}║${NC}                                                          ${CYAN}║${NC}"
echo -e "  ${CYAN}║${NC}   ${DIM}Your private space for shared memories${NC}                 ${CYAN}║${NC}"
echo -e "  ${CYAN}║${NC}                                                          ${CYAN}║${NC}"
echo -e "  ${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
if $VERBOSE; then
    info "Verbose mode enabled — showing command output"
    echo ""
fi

# ── Detect Package Manager ───────────────────────────────────────────────────
if command -v apt-get &>/dev/null; then
    PKG_MANAGER="apt"
    PKG_UPDATE="apt-get update"
    PKG_INSTALL="apt-get install -y"
elif command -v dnf &>/dev/null; then
    PKG_MANAGER="dnf"
    PKG_UPDATE="dnf check-update || true"
    PKG_INSTALL="dnf install -y"
elif command -v yum &>/dev/null; then
    PKG_MANAGER="yum"
    PKG_UPDATE="yum check-update || true"
    PKG_INSTALL="yum install -y"
else
    fail "Unsupported package manager. This script supports apt (Debian/Ubuntu), dnf (Fedora/Rocky), and yum (CentOS)."
fi

success "Detected package manager: ${BOLD}${PKG_MANAGER}${NC}"

# ── Interactive Setup ────────────────────────────────────────────────────────

step "Configuration"

INSTALL_DIR_DEFAULT="/opt/sharedmoments"
ask "Installation directory" "$INSTALL_DIR_DEFAULT" INSTALL_DIR

ask "Domain or IP (e.g. moments.example.com)" "localhost" DOMAIN

ask "Port" "5001" PORT

GIT_REPO_URL="https://github.com/tech-kev/SharedMoments.git"

ask "Git Branch" "main" GIT_BRANCH

GIT_BRANCH="v2.0-rebuild"

ask_choice "Edition" "Couples|Family|Friends" "1" EDITION
EDITION_LOWER=$(echo "$EDITION" | tr '[:upper:]' '[:lower:]')

ask_choice "Database" "SQLite (recommended)|MySQL (external)" "1" DB_CHOICE

DB_URL=""
if [[ "$DB_CHOICE" == *"MySQL"* ]]; then
    ask "MySQL Host" "localhost" MYSQL_HOST
    ask "MySQL Port" "3306" MYSQL_PORT
    ask "MySQL Database" "sharedmoments" MYSQL_DB
    ask "MySQL User" "sharedmoments" MYSQL_USER
    ask_secret "MySQL Password" MYSQL_PASS
    DB_URL="mysql+mysqlconnector://${MYSQL_USER}:${MYSQL_PASS}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DB}"
fi

echo ""
info "Optional: Configure notification channels (press Enter to skip)"
ask "SMTP Host (for email notifications)" "" SMTP_HOST
SMTP_PORT=""
SMTP_USER=""
SMTP_PASS=""
SMTP_FROM=""
if [[ -n "$SMTP_HOST" ]]; then
    ask "SMTP Port" "587" SMTP_PORT
    ask "SMTP User" "" SMTP_USER
    ask_secret "SMTP Password" SMTP_PASS
    ask "SMTP From address" "$SMTP_USER" SMTP_FROM
fi

ask "Telegram Bot Token (for Telegram notifications)" "" TELEGRAM_BOT_TOKEN

echo ""
info "Optional: Configure AI features (press Enter to skip)"
ask "OpenAI API Key" "" OPENAI_API_KEY
ask "Anthropic API Key" "" ANTHROPIC_API_KEY

# Generate secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)

# Determine WebAuthn settings
if [[ "$DOMAIN" == "localhost" || "$DOMAIN" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    WEBAUTHN_RP_ID="localhost"
    WEBAUTHN_ORIGIN="http://${DOMAIN}:${PORT}"
else
    WEBAUTHN_RP_ID="$DOMAIN"
    WEBAUTHN_ORIGIN="https://${DOMAIN}"
fi

# ── Summary before install ───────────────────────────────────────────────────

step "Installation Summary"

echo -e "  ${DIM}┌─────────────────────────────────────────────────────┐${NC}"
echo -e "  ${DIM}│${NC}  Directory:    ${BOLD}${INSTALL_DIR}${NC}"
echo -e "  ${DIM}│${NC}  Domain:       ${BOLD}${DOMAIN}:${PORT}${NC}"
echo -e "  ${DIM}│${NC}  Branch:       ${BOLD}${GIT_BRANCH}${NC}"
echo -e "  ${DIM}│${NC}  Edition:      ${BOLD}${EDITION}${NC}"
if [[ -n "$DB_URL" ]]; then
echo -e "  ${DIM}│${NC}  Database:     ${BOLD}MySQL${NC}"
else
echo -e "  ${DIM}│${NC}  Database:     ${BOLD}SQLite${NC}"
fi
echo -e "  ${DIM}│${NC}  Notifications:${BOLD}$([ -n "$SMTP_HOST" ] && echo " Email")$([ -n "$TELEGRAM_BOT_TOKEN" ] && echo " Telegram")$([ -z "$SMTP_HOST" ] && [ -z "$TELEGRAM_BOT_TOKEN" ] && echo " None")${NC}"
echo -e "  ${DIM}│${NC}  AI:           ${BOLD}$([ -n "$OPENAI_API_KEY" ] && echo " OpenAI")$([ -n "$ANTHROPIC_API_KEY" ] && echo " Anthropic")$([ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && echo " None")${NC}"
echo -e "  ${DIM}└─────────────────────────────────────────────────────┘${NC}"
echo ""
echo -ne "  ${BOLD}Proceed with installation? [Y/n]${NC}: "
read -r confirm < /dev/tty
if [[ "${confirm,,}" == "n" ]]; then
    info "Installation cancelled."
    exit 0
fi

# ── Step 1: System Dependencies ──────────────────────────────────────────────

step "Step 1/6 — Installing system dependencies" 1
info "Updating package lists and installing python3, ffmpeg, git etc. — this may take a few minutes..."

_task_install_packages() {
    $PKG_UPDATE
    if [[ "$PKG_MANAGER" == "apt" ]]; then
        $PKG_INSTALL python3 python3-pip python3-venv python3-dev ffmpeg git build-essential libffi-dev libssl-dev
    else
        $PKG_INSTALL python3 python3-pip python3-devel ffmpeg git gcc libffi-devel openssl-devel
    fi
}
run_task "Installing system packages..." _task_install_packages
success "System dependencies installed"

# Verify Python version
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [[ "$PYTHON_MAJOR" -lt 3 ]] || [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -lt 10 ]]; then
    fail "Python 3.10+ is required (found ${PYTHON_VERSION})"
fi
success "Python ${PYTHON_VERSION} found"

# ── Step 2: Create User & Directory ──────────────────────────────────────────

step "Step 2/6 — Setting up application directory" 2
info "Creating system user, cloning repository and setting up directories..."

# Create system user if not exists
if ! id -u sharedmoments &>/dev/null; then
    useradd --system --shell /usr/sbin/nologin --home-dir "$INSTALL_DIR" sharedmoments
    success "Created system user: sharedmoments"
else
    success "System user sharedmoments already exists"
fi

# Resolve script source directory (for local fallback copy)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find local source (check script dir, then cwd)
LOCAL_SRC=""
if [[ -f "$SCRIPT_DIR/run.py" ]]; then
    LOCAL_SRC="$SCRIPT_DIR"
elif [[ -f "$(pwd)/run.py" ]]; then
    LOCAL_SRC="$(pwd)"
fi

# Clone or copy repository
if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Directory exists, pulling latest changes..."
    cd "$INSTALL_DIR"
    git checkout "$GIT_BRANCH" --quiet 2>/dev/null || true
    sudo -u sharedmoments git pull --quiet 2>/dev/null || git pull --quiet
    success "Repository updated (branch: ${GIT_BRANCH})"
elif [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/run.py" ]]; then
    warn "Directory exists but is not a git repo — using existing files"
else
    # Remove empty dir if it exists (git clone needs non-existing or empty target)
    [[ -d "$INSTALL_DIR" ]] && rmdir "$INSTALL_DIR" 2>/dev/null || true

    info "Cloning ${GIT_REPO_URL} (branch: ${GIT_BRANCH})..."
    CLONE_ERR=$(GIT_TERMINAL_PROMPT=0 git clone --branch "$GIT_BRANCH" "$GIT_REPO_URL" "$INSTALL_DIR" 2>&1) && success "Repository cloned (branch: ${GIT_BRANCH})" || {
        # Show git error
        warn "git clone failed: ${CLONE_ERR}"

        # If clone fails, copy from local directory
        if [[ -n "$LOCAL_SRC" ]]; then
            info "Falling back to local directory (${LOCAL_SRC})..."
            mkdir -p "$INSTALL_DIR"
            cp -r "$LOCAL_SRC"/* "$INSTALL_DIR"/
            cp -r "$LOCAL_SRC"/.env.example "$INSTALL_DIR"/ 2>/dev/null || true
            # Init git repo for future updates
            cd "$INSTALL_DIR" && git init --quiet && git add -A && git commit --quiet -m "Initial install from local copy" 2>/dev/null || true
            success "Files copied from local directory"
        else
            fail "Could not clone repository and no local source found.\n     Make sure the GitHub repo is accessible, or run this script from the SharedMoments directory."
        fi
    }
fi

# Create required directories
mkdir -p "$INSTALL_DIR"/{app/database,app/uploads/{images,videos,music,thumbs,temp,profiles},app/migration_data,export,logs}

chown -R sharedmoments:sharedmoments "$INSTALL_DIR"
success "Directory structure created"

# ── Step 3: Python Environment ───────────────────────────────────────────────

step "Step 3/6 — Setting up Python environment" 3
info "Creating virtual environment and installing dependencies — this may take a few minutes..."

cd "$INSTALL_DIR"

if [[ ! -d "$INSTALL_DIR/.venv" ]]; then
    python3 -m venv "$INSTALL_DIR/.venv"
    success "Virtual environment created"
else
    success "Virtual environment exists"
fi

_task_install_pip() {
    "$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    "$INSTALL_DIR/.venv/bin/pip" install gunicorn
}
run_task "Installing Python dependencies..." _task_install_pip
success "Python dependencies installed"

# ── Step 4: Configuration ────────────────────────────────────────────────────

step "Step 4/6 — Creating configuration" 4

cat > "$INSTALL_DIR/.env" << ENVEOF
# ╔════════════════════════════════════════════════╗
# ║  SharedMoments v2 — Configuration             ║
# ║  Generated by install.sh on $(date +%Y-%m-%d)          ║
# ╚════════════════════════════════════════════════╝

# Core
SECRET_KEY=${SECRET_KEY}
PORT=${PORT}

# Database (leave empty for SQLite)
DATABASE_URL=${DB_URL}

# WebAuthn / Passkeys
WEBAUTHN_RP_ID=${WEBAUTHN_RP_ID}
WEBAUTHN_RP_NAME=SharedMoments
WEBAUTHN_ORIGIN=${WEBAUTHN_ORIGIN}

# Notifications — SMTP
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=${SMTP_PORT}
SMTP_USER=${SMTP_USER}
SMTP_PASS=${SMTP_PASS}
SMTP_FROM=${SMTP_FROM}

# Notifications — Telegram
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}

# AI Providers (optional)
OPENAI_API_KEY=${OPENAI_API_KEY}
OPENAI_MODEL=gpt-4o-mini
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
ANTHROPIC_MODEL=claude-haiku-4-5
ENVEOF

chown sharedmoments:sharedmoments "$INSTALL_DIR/.env"
chmod 600 "$INSTALL_DIR/.env"
success "Configuration file created (.env)"

# ── Step 5: Initialize Database ──────────────────────────────────────────────

step "Step 5/6 — Initializing database" 5
info "Creating tables, loading translations, generating VAPID keys..."

_task_init_db() {
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

# Set edition
from app.db_queries import update_setting
update_setting('sm_edition', '${EDITION_LOWER}')
"
}
run_task "Initializing database..." _task_init_db
success "Database initialized (edition: ${EDITION})"

# ── Step 6: Systemd Service ──────────────────────────────────────────────────

step "Step 6/6 — Creating systemd service" 6
info "Writing service file, enabling and starting SharedMoments..."

cat > /etc/systemd/system/sharedmoments.service << SERVICEEOF
[Unit]
Description=SharedMoments v2
Documentation=https://github.com/tech-kev/SharedMoments
After=network.target
Wants=network-online.target

[Service]
Type=exec
User=sharedmoments
Group=sharedmoments
WorkingDirectory=${INSTALL_DIR}
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${INSTALL_DIR}/.venv/bin/gunicorn \\
    --bind 0.0.0.0:${PORT} \\
    --workers 4 \\
    --threads 2 \\
    --timeout 300 \\
    --access-logfile ${INSTALL_DIR}/logs/access.log \\
    --error-logfile ${INSTALL_DIR}/logs/error.log \\
    run:app
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=5s

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=${INSTALL_DIR}
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICEEOF

systemctl daemon-reload
systemctl enable --quiet sharedmoments
systemctl start sharedmoments

# Wait for service to come up
sleep 2
if systemctl is-active --quiet sharedmoments; then
    success "Service started and enabled"
else
    warn "Service may not have started. Check: ${BOLD}journalctl -u sharedmoments -n 50${NC}"
fi

# ── Done ─────────────────────────────────────────────────────────────────────

echo ""
echo ""
echo -e "  ${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}   ${BOLD}${GREEN}✔  Installation complete!${NC}                              ${GREEN}║${NC}"
echo -e "  ${GREEN}║${NC}                                                          ${GREEN}║${NC}"
echo -e "  ${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Access your instance:${NC}"
if [[ "$DOMAIN" == "localhost" ]]; then
    echo -e "    ${CYAN}➜${NC}  http://localhost:${PORT}"
else
    echo -e "    ${CYAN}➜${NC}  https://${DOMAIN}"
fi
echo ""
echo -e "  ${BOLD}First steps:${NC}"
echo -e "    ${DIM}1.${NC} Open the URL above — the setup wizard will guide you"
echo -e "    ${DIM}2.${NC} Create your first user account with email & password"
echo -e "    ${DIM}3.${NC} Optionally set up a reverse proxy (nginx/caddy) for HTTPS"
echo ""
echo -e "  ${BOLD}Useful commands:${NC}"
echo -e "    ${DIM}Status:${NC}    systemctl status sharedmoments"
echo -e "    ${DIM}Logs:${NC}      journalctl -u sharedmoments -f"
echo -e "    ${DIM}Restart:${NC}   systemctl restart sharedmoments"
echo -e "    ${DIM}Update:${NC}    bash ${INSTALL_DIR}/update.sh"
echo -e "    ${DIM}Uninstall:${NC} bash ${INSTALL_DIR}/uninstall.sh"
echo ""
echo -e "  ${BOLD}Files:${NC}"
echo -e "    ${DIM}Config:${NC}    ${INSTALL_DIR}/.env"
echo -e "    ${DIM}Database:${NC}  ${INSTALL_DIR}/app/database/"
echo -e "    ${DIM}Uploads:${NC}   ${INSTALL_DIR}/app/uploads/"
echo -e "    ${DIM}Logs:${NC}      ${INSTALL_DIR}/logs/"
echo ""
echo -e "  ${DIM}────────────────────────────────────────────────────────${NC}"
echo -e "  ${DIM}SharedMoments v2 • https://github.com/tech-kev/SharedMoments${NC}"
echo ""
