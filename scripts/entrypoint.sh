#!/bin/bash
set -e

# ==============================================================================
# HolyCode - Container Entrypoint
# Handles: UID/GID remapping, directory pre-creation, first-boot bootstrap,
#          s6-overlay handoff
# ==============================================================================

OC_USER="opencode"
OC_HOME="/home/opencode"
WORKSPACE_DIR="/workspace"

# ---------- UID/GID remapping ----------
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

CURRENT_UID=$(id -u "$OC_USER")
CURRENT_GID=$(id -g "$OC_USER")

if [ "$PGID" != "$CURRENT_GID" ]; then
    echo "[entrypoint] Changing opencode GID from $CURRENT_GID to $PGID"
    groupmod -o -g "$PGID" opencode
fi

if [ "$PUID" != "$CURRENT_UID" ]; then
    echo "[entrypoint] Changing opencode UID from $CURRENT_UID to $PUID"
    usermod -o -u "$PUID" opencode
fi

# ---------- Fix home directory ownership ----------
chown "$PUID:$PGID" "$OC_HOME"

# Pre-create OpenCode directories (bind mount may start empty)
for dir in \
    "$OC_HOME/.config/opencode" \
    "$OC_HOME/.config/opencode/skills" \
    "$OC_HOME/.local/share/opencode" \
    "$OC_HOME/.local/state/opencode" \
    "$OC_HOME/.cache/opencode" \
    "$OC_HOME/.claude"; do
    mkdir -p "$dir"
    chown "$PUID:$PGID" "$dir"
done
chown "$PUID:$PGID" "$OC_HOME/.config" "$OC_HOME/.local" "$OC_HOME/.local/share" "$OC_HOME/.local/state" "$OC_HOME/.cache" 2>/dev/null || true

# ---------- Ensure /workspace is writable ----------
mkdir -p "$WORKSPACE_DIR"
if ! runuser -u "$OC_USER" -- test -w "$WORKSPACE_DIR"; then
    echo "[entrypoint] /workspace is not writable for $OC_USER, attempting ownership fix"
    chown "$PUID:$PGID" "$WORKSPACE_DIR" 2>/dev/null || true
fi

if ! runuser -u "$OC_USER" -- test -w "$WORKSPACE_DIR"; then
    echo "[entrypoint] WARNING: /workspace is still not writable; fix host ownership or PUID/PGID"
fi

check_cifs_compatibility() {
    [ -d "$OC_HOME" ] || return 0
    local test_db
    test_db=$(mktemp "${OC_HOME}/.holycode-wal-test-XXXXXX.db" 2>/dev/null) || return 0

    if python3 - "$test_db" 2>/dev/null <<'PY'; then
import sqlite3
import sys

db_path = sys.argv[1]
db = sqlite3.connect(db_path)
db.execute('PRAGMA journal_mode=WAL')
db.execute('CREATE TABLE _t (id INTEGER)')
db.execute('INSERT INTO _t VALUES (1)')
db.commit()
db2 = sqlite3.connect(db_path)
db2.execute('SELECT * FROM _t').fetchall()
db2.close()
db.execute('PRAGMA journal_mode=DELETE')
db.close()
PY
        rm -f "$test_db" "${test_db}-wal" "${test_db}-shm" 2>/dev/null || true
        return 0
    fi

    rm -f "$test_db" "${test_db}-wal" "${test_db}-shm" 2>/dev/null || true
    echo ""
    echo "============================================================"
    echo "  WARNING: SQLite WAL locking failed on this mount"
    echo "============================================================"
    echo "  If your data directory is on CIFS/SMB, add 'nobrl,mfsymlinks'"
    echo "  to mount options in /etc/fstab on the host, then remount."
    echo "============================================================"
    echo ""
}

check_cifs_compatibility

# ---------- First-boot bootstrap ----------
SENTINEL="$OC_HOME/.config/opencode/.holycode-bootstrapped"
if [ ! -f "$SENTINEL" ]; then
    echo "[entrypoint] First boot detected, running bootstrap.sh"
    if ! /usr/local/bin/bootstrap.sh; then
        echo "[entrypoint] WARNING: bootstrap.sh failed, continuing anyway"
    fi
fi

# ---------- Hand off to s6-overlay ----------
echo "[entrypoint] Starting s6-overlay..."
exec /init "$@"
