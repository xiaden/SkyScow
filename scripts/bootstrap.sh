#!/bin/bash
set -e

# ==============================================================================
# HolyCode - First-Boot Bootstrap
# Runs once on first container start, then creates a sentinel to skip next time.
# Delete ~/.config/opencode/.holycode-bootstrapped to re-trigger.
# ==============================================================================

OC_HOME="/home/opencode"
OC_USER="opencode"
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
SOURCE_DIR="/usr/local/share/holycode"

echo "[bootstrap] Running first-boot initialization..."

# ---------- Copy default opencode.json ----------
if [ ! -f "$OC_HOME/.config/opencode/opencode.json" ]; then
    cp "$SOURCE_DIR/opencode.json" "$OC_HOME/.config/opencode/opencode.json"
    echo "[bootstrap] Copied default opencode.json"
else
    echo "[bootstrap] opencode.json already exists, skipping"
fi

# ---------- Copy shipped plugins ----------
SOURCE_PLUGIN_DIR="$SOURCE_DIR/plugins"
TARGET_PLUGIN_DIR="$OC_HOME/.config/opencode/plugins"
if [ -d "$SOURCE_PLUGIN_DIR" ] && [ -z "$(ls -A "$TARGET_PLUGIN_DIR" 2>/dev/null)" ]; then
    mkdir -p "$TARGET_PLUGIN_DIR"
    cp -R "$SOURCE_PLUGIN_DIR/." "$TARGET_PLUGIN_DIR/"
    chown -R "$PUID:$PGID" "$TARGET_PLUGIN_DIR"
    echo "[bootstrap] Copied shipped plugins"
fi

# ---------- Copy shipped agents ----------
SOURCE_AGENTS_DIR="$SOURCE_DIR/agents"
TARGET_AGENTS_DIR="$OC_HOME/.config/opencode/agents"
if [ -d "$SOURCE_AGENTS_DIR" ] && [ -z "$(ls -A "$TARGET_AGENTS_DIR" 2>/dev/null)" ]; then
    mkdir -p "$TARGET_AGENTS_DIR"
    cp -R "$SOURCE_AGENTS_DIR/." "$TARGET_AGENTS_DIR/"
    chown -R "$PUID:$PGID" "$TARGET_AGENTS_DIR"
    echo "[bootstrap] Copied shipped agents"
fi

# ---------- Copy shipped skills ----------
SOURCE_SKILLS_DIR="$SOURCE_DIR/skills"
TARGET_SKILLS_DIR="$OC_HOME/.config/opencode/skills"
if [ -d "$SOURCE_SKILLS_DIR" ] && [ -z "$(ls -A "$TARGET_SKILLS_DIR" 2>/dev/null)" ]; then
    mkdir -p "$TARGET_SKILLS_DIR"
    cp -R "$SOURCE_SKILLS_DIR/." "$TARGET_SKILLS_DIR/"
    chown -R "$PUID:$PGID" "$TARGET_SKILLS_DIR"
    echo "[bootstrap] Copied shipped skills"
fi

# ---------- Copy shipped tools ----------
SOURCE_TOOLS_DIR="$SOURCE_DIR/tools"
TARGET_TOOLS_DIR="$OC_HOME/.config/opencode/tools"
if [ -d "$SOURCE_TOOLS_DIR" ] && [ -z "$(ls -A "$TARGET_TOOLS_DIR" 2>/dev/null)" ]; then
    mkdir -p "$TARGET_TOOLS_DIR"
    cp -R "$SOURCE_TOOLS_DIR/." "$TARGET_TOOLS_DIR/"
    chown -R "$PUID:$PGID" "$TARGET_TOOLS_DIR"
    echo "[bootstrap] Copied shipped tools"
fi

# ---------- Copy shipped commands ----------
SOURCE_COMMANDS_DIR="$SOURCE_DIR/commands"
TARGET_COMMANDS_DIR="$OC_HOME/.config/opencode/commands"
if [ -d "$SOURCE_COMMANDS_DIR" ] && [ -z "$(ls -A "$TARGET_COMMANDS_DIR" 2>/dev/null)" ]; then
    mkdir -p "$TARGET_COMMANDS_DIR"
    cp -R "$SOURCE_COMMANDS_DIR/." "$TARGET_COMMANDS_DIR/"
    chown -R "$PUID:$PGID" "$TARGET_COMMANDS_DIR"
    echo "[bootstrap] Copied shipped commands"
fi

# ---------- Git configuration ----------
GIT_USER_NAME="${GIT_USER_NAME:-HolyCode User}"
GIT_USER_EMAIL="${GIT_USER_EMAIL:-noreply@holycode.local}"
runuser -u "$OC_USER" -- git config --global safe.directory /workspace
runuser -u "$OC_USER" -- git config --global user.name "$GIT_USER_NAME"
runuser -u "$OC_USER" -- git config --global user.email "$GIT_USER_EMAIL"
echo "[bootstrap] Configured git as '$GIT_USER_NAME <$GIT_USER_EMAIL>'"

# ---------- Fix ownership ----------
chown -R "$PUID:$PGID" "$OC_HOME/.config/opencode"
chown -R "$PUID:$PGID" "$OC_HOME/.local/share/opencode"
chown -R "$PUID:$PGID" "$OC_HOME/.local/state/opencode"
chown -R "$PUID:$PGID" "$OC_HOME/.cache/opencode"

# ---------- Create sentinel ----------
touch "$OC_HOME/.config/opencode/.holycode-bootstrapped"
chown "$PUID:$PGID" "$OC_HOME/.config/opencode/.holycode-bootstrapped"

echo "[bootstrap] First-boot initialization complete."
