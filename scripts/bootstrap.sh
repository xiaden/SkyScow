#!/bin/bash
set -euo pipefail

# ==============================================================================
# HolyCode - Version-aware configuration bootstrap
#
# The image ships a manifest alongside its OpenCode configuration. This script
# reconciles that manifest with the persistent home directory on every start.
# A file is image-owned only while its local content still matches the last
# shipped hash. User-edited, user-deleted, and previously unknown files remain.
# ==============================================================================

OC_HOME="${OC_HOME:-/home/opencode}"
OC_USER="${OC_USER:-opencode}"
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
SOURCE_DIR="${SOURCE_DIR:-/usr/local/share/holycode}"
SOURCE_MANIFEST="${SOURCE_MANIFEST:-$SOURCE_DIR/bootstrap-manifest.tsv}"
CONFIG_DIR="$OC_HOME/.config/opencode"
STATE_DIR="$OC_HOME/.local/state/opencode"
STATE_MANIFEST="${STATE_MANIFEST:-$STATE_DIR/.holycode-bootstrap-manifest.tsv}"
LOCK_FILE="$STATE_DIR/.holycode-bootstrap.lock"
MODE="${1:-auto}"

case "$MODE" in
    auto) DRY_RUN=0; INTERACTIVE=0 ;;
    --check) DRY_RUN=1; INTERACTIVE=0 ;;
    --interactive) DRY_RUN=0; INTERACTIVE=1 ;;
    *)
        echo "Usage: bootstrap.sh [--check|--interactive]" >&2
        exit 2
        ;;
esac

declare -A SOURCE_HASHES=()
declare -A PREVIOUS_HASHES=()
declare -A PREVIOUS_OWNERS=()
declare -A PREVIOUS_VERSIONS=()
declare -A NEXT_HASHES=()
declare -A NEXT_OWNERS=()
declare -A NEXT_VERSIONS=()
declare -A PENDING_ACTIONS=()
RECONCILIATION_QUIT=0

SOURCE_VERSION="0.0.0"
PREVIOUS_VERSION="0.0.0"

log() {
    echo "[bootstrap] $*"
}

die() {
    echo "[bootstrap] ERROR: $*" >&2
    exit 1
}

safe_relative_path() {
    local path="$1"
    case "$path" in
        ""|/*|../*|*/../*|*/..|*$'\t'*) return 1 ;;
    esac
    return 0
}

hash_file() {
    sha256sum -- "$1" | cut -d' ' -f1
}

target_path() {
    printf '%s/%s' "$CONFIG_DIR" "$1"
}

target_present() {
    [[ -e "$1" || -L "$1" ]]
}

load_source_manifest() {
    [[ -f "$SOURCE_MANIFEST" ]] || die "missing shipped manifest: $SOURCE_MANIFEST"

    local kind path hash
    while IFS=$'\t' read -r kind path hash; do
        [[ -n "$kind" ]] || continue
        case "$kind" in
            schema)
                [[ "$path" == "1" ]] || die "unsupported shipped manifest schema: $path"
                ;;
            version)
                SOURCE_VERSION="${path:-0.0.0}"
                ;;
            file)
                safe_relative_path "$path" || die "unsafe path in shipped manifest: $path"
                [[ "$hash" =~ ^[[:xdigit:]]{64}$ ]] || die "invalid hash in shipped manifest: $path"
                SOURCE_HASHES["$path"]="$hash"
                ;;
            "") ;;
            *) die "unknown record in shipped manifest: $kind" ;;
        esac
    done < "$SOURCE_MANIFEST"
}

load_previous_manifest() {
    [[ -f "$STATE_MANIFEST" ]] || return 0

    local kind path hash owner version
    while IFS=$'\t' read -r kind path hash owner version; do
        [[ -n "$kind" ]] || continue
        case "$kind" in
            schema)
                [[ "$path" == "1" ]] || die "unsupported state manifest schema: $path"
                ;;
            version)
                PREVIOUS_VERSION="${path:-0.0.0}"
                ;;
            file)
                safe_relative_path "$path" || die "unsafe path in state manifest: $path"
                [[ "$owner" == "shipped" || "$owner" == "user" || "$owner" == "legacy" || "$owner" == "deleted" ]] || die "invalid owner in state manifest: $path"
                PREVIOUS_HASHES["$path"]="$hash"
                PREVIOUS_OWNERS["$path"]="$owner"
                PREVIOUS_VERSIONS["$path"]="${version:-0.0.0}"
                ;;
            "") ;;
            *) die "unknown record in state manifest: $kind" ;;
        esac
    done < "$STATE_MANIFEST"
}

previous_has() {
    [[ -n "${PREVIOUS_OWNERS[$1]+present}" ]]
}

record_next() {
    local path="$1" hash="$2" owner="$3" version="$4"
    NEXT_HASHES["$path"]="$hash"
    NEXT_OWNERS["$path"]="$owner"
    NEXT_VERSIONS["$path"]="$version"
}

schedule_action() {
    local path="$1" action="$2"
    if [[ "$INTERACTIVE" == 1 ]]; then
        PENDING_ACTIONS["$path"]="$action"
    fi
}

apply_pending_actions() {
    [[ "$INTERACTIVE" == 1 ]] || return 0

    local path action
    while IFS= read -r path; do
        action="${PENDING_ACTIONS[$path]}"
        case "$action" in
            copy)
                copy_shipped "$path"
                log "installed/updated $path"
                ;;
            remove)
                remove_shipped "$path"
                log "removed obsolete $path"
                ;;
            *)
                die "unknown pending reconciliation action: $action"
                ;;
        esac
    done < <(printf '%s\n' "${!PENDING_ACTIONS[@]}" | LC_ALL=C sort)
}

show_current_diff() {
    local path="$1" target source diff_status=0 diff_output
    target="$(target_path "$path")"
    source="$SOURCE_DIR/$path"

    # git diff --no-index returns 1 when files differ. Its --label option is
    # not available in all Git versions, so normalize the portable headers.
    set +e
    diff_output="$(git diff --no-index --no-ext-diff -- "$target" "$source")"
    diff_status=$?
    set -e
    if [[ "$diff_status" -le 1 ]]; then
        printf '%s\n' "$diff_output" | sed \
            -e '1s|^--- .*|--- LOCAL|' \
            -e "2s|^+++ .*|+++ SHIPPED $SOURCE_VERSION|"
    fi
    if [[ "$diff_status" -gt 1 ]]; then
        log "unable to show diff for $path (status $diff_status)"
    fi
}

prompt_current_conflict() {
    local path="$1" answer
    [[ -e /dev/tty ]] || die "interactive mode requires a terminal"

    printf '\n================================================================\n'
    printf '%s\n' "$path"
    printf 'Local file differs from shipped %s\n' "$SOURCE_VERSION"
    printf '================================================================\n\n'
    show_current_diff "$path"
    while true; do
        read -r -p $'\n[k] keep local  [u] use shipped  [q] quit\nChoice: ' answer < /dev/tty || return 3
        case "$answer" in
            k|K) return 0 ;;
            u|U) return 1 ;;
            q|Q) return 3 ;;
            *) printf 'Please choose k, u, or q.\n' ;;
        esac
    done
}

prompt_obsolete() {
    local path="$1" local_hash="$2" previous_hash="$3" previous_owner="$4" previous_version="$5" answer
    [[ -e /dev/tty ]] || die "interactive mode requires a terminal"

    printf '\n================================================================\n'
    printf '%s\n' "$path"
    printf 'Obsolete: no longer shipped in %s\n' "$SOURCE_VERSION"
    if [[ "$previous_owner" == "shipped" ]]; then
        printf 'Previous shipped version: %s\n' "$previous_version"
        printf 'Local SHA256: %s\nPrevious shipped SHA256: %s\n' "$local_hash" "$previous_hash"
        printf 'Previous shipped content is not available for a diff.\n'
    else
        printf 'Local SHA256: %s\n' "$local_hash"
        printf 'Previous shipped content is not available for a diff.\n'
    fi
    printf '================================================================\n'
    while true; do
        read -r -p $'\n[k] keep local  [d] delete obsolete  [q] quit\nChoice: ' answer < /dev/tty || return 3
        case "$answer" in
            k|K) return 0 ;;
            d|D) return 1 ;;
            q|Q) return 3 ;;
            *) printf 'Please choose k, d, or q.\n' ;;
        esac
    done
}

copy_shipped() {
    local path="$1" source target
    source="$SOURCE_DIR/$path"
    target="$(target_path "$path")"
    if [[ -L "$target" ]]; then
        log "preserving symlink instead of replacing $path"
        return 1
    fi
    if [[ "$DRY_RUN" == 1 ]]; then
        log "would install/update $path"
        return 0
    fi
    mkdir -p "$(dirname "$target")"

    local temporary
    temporary="$(mktemp "${target}.holycode.XXXXXX")"
    cp -a -- "$source" "$temporary"
    mv -f -- "$temporary" "$target"
}

remove_shipped() {
    local path="$1" target
    target="$(target_path "$path")"
    if [[ "$DRY_RUN" == 1 ]]; then
        log "would remove obsolete $path"
        return 0
    fi
    rm -f -- "$target"
}

reconcile_current_file() {
    local path="$1" shipped_hash="${SOURCE_HASHES[$1]}" target local_hash previous_hash previous_owner
    target="$(target_path "$path")"

    if ! target_present "$target"; then
        if previous_has "$path"; then
            log "preserving user-deleted $path"
            record_next "$path" "$shipped_hash" deleted "$SOURCE_VERSION"
        elif [[ "$INTERACTIVE" == 1 ]]; then
            schedule_action "$path" copy
            record_next "$path" "$shipped_hash" shipped "$SOURCE_VERSION"
        elif copy_shipped "$path"; then
            [[ "$DRY_RUN" == 1 ]] || log "installed $path"
            record_next "$path" "$shipped_hash" shipped "$SOURCE_VERSION"
        else
            log "preserving unknown target for $path"
            record_next "$path" "-" user "$SOURCE_VERSION"
        fi
        return
    fi

    if [[ -L "$target" ]]; then
        log "preserving user symlink $path"
        record_next "$path" "-" user "$SOURCE_VERSION"
        return
    fi
    if [[ -d "$target" ]]; then
        log "preserving user directory blocking $path"
        record_next "$path" "-" user "$SOURCE_VERSION"
        return
    fi

    local_hash="$(hash_file "$target")"
    if [[ "$local_hash" == "$shipped_hash" ]]; then
        record_next "$path" "$shipped_hash" shipped "$SOURCE_VERSION"
        return
    fi

    previous_hash="${PREVIOUS_HASHES[$path]:-}"
    previous_owner="${PREVIOUS_OWNERS[$path]:-}"
    if [[ "$previous_owner" == "shipped" && "$local_hash" == "$previous_hash" ]]; then
        if [[ "$INTERACTIVE" == 1 ]]; then
            schedule_action "$path" copy
            record_next "$path" "$shipped_hash" shipped "$SOURCE_VERSION"
            return
        elif copy_shipped "$path"; then
            if [[ "$DRY_RUN" == 0 ]]; then
                log "updated $path ($PREVIOUS_VERSION -> $SOURCE_VERSION)"
            fi
            record_next "$path" "$shipped_hash" shipped "$SOURCE_VERSION"
            return
        fi
    else
        if [[ "$INTERACTIVE" == 1 ]]; then
            local choice
            if prompt_current_conflict "$path"; then
                choice=0
            else
                choice=$?
            fi
            case "$choice" in
                0)
                    log "keeping local $path"
                    record_next "$path" "$local_hash" user "$SOURCE_VERSION"
                    return
                    ;;
                1)
                    schedule_action "$path" copy
                    record_next "$path" "$shipped_hash" shipped "$SOURCE_VERSION"
                    return
                    ;;
                3)
                    RECONCILIATION_QUIT=1
                    return 0
                    ;;
            esac
        fi
        log "preserving edited $path"
    fi
    record_next "$path" "$local_hash" user "$SOURCE_VERSION"
}

reconcile_obsolete_file() {
    local path="$1" target local_hash previous_hash previous_owner previous_version
    target="$(target_path "$path")"
    target_present "$target" || return

    if [[ -L "$target" ]]; then
        if [[ "$INTERACTIVE" == 1 && "${PREVIOUS_OWNERS[$path]+present}" == present ]]; then
            local choice
            if prompt_obsolete "$path" "-" "${PREVIOUS_HASHES[$path]:--}" \
                "${PREVIOUS_OWNERS[$path]:-user}" "${PREVIOUS_VERSIONS[$path]:-0.0.0}"; then
                choice=0
            else
                choice=$?
            fi
            case "$choice" in
                0) record_next "$path" "-" user "${PREVIOUS_VERSIONS[$path]:-0.0.0}"; return ;;
                1) schedule_action "$path" remove; return ;;
                3) RECONCILIATION_QUIT=1; return ;;
            esac
        fi
        log "preserving unknown symlink $path"
        record_next "$path" "-" user "$SOURCE_VERSION"
        return
    fi

    local_hash="$(hash_file "$target")"
    if ! previous_has "$path"; then
        # Existing installations have no file-level provenance. V0.0.0 is the
        # explicit legacy origin; preserve the file until a human decides.
        log "preserving legacy V0.0.0 file $path"
        record_next "$path" "$local_hash" legacy "0.0.0"
        return
    fi

    previous_hash="${PREVIOUS_HASHES[$path]:-}"
    previous_owner="${PREVIOUS_OWNERS[$path]:-}"
    previous_version="${PREVIOUS_VERSIONS[$path]:-0.0.0}"
    if [[ "$previous_owner" == "shipped" && "$local_hash" == "$previous_hash" ]]; then
        if [[ "$INTERACTIVE" == 1 ]]; then
            local choice
            if prompt_obsolete "$path" "$local_hash" "$previous_hash" "$previous_owner" "$previous_version"; then
                choice=0
            else
                choice=$?
            fi
            case "$choice" in
                0)
                    record_next "$path" "$local_hash" user "$previous_version"
                    return
                    ;;
                1)
                    schedule_action "$path" remove
                    return
                    ;;
                3)
                    RECONCILIATION_QUIT=1
                    return 0
                    ;;
            esac
        elif remove_shipped "$path"; then
            [[ "$DRY_RUN" == 1 ]] || log "removed obsolete $path"
            return
        fi
    else
        if [[ "$INTERACTIVE" == 1 ]]; then
            local choice
            if prompt_obsolete "$path" "$local_hash" "$previous_hash" "$previous_owner" "$previous_version"; then
                choice=0
            else
                choice=$?
            fi
            case "$choice" in
                0)
                    record_next "$path" "$local_hash" user "$previous_version"
                    return
                    ;;
                1)
                    schedule_action "$path" remove
                    return
                    ;;
                3)
                    RECONCILIATION_QUIT=1
                    return 0
                    ;;
            esac
        fi
        log "preserving edited/legacy obsolete $path"
    fi
    record_next "$path" "$local_hash" "$previous_owner" "$previous_version"
}

reconcile_unknown_files() {
    local root target path
    for root in agents plugins skills tools commands; do
        [[ -d "$CONFIG_DIR/$root" ]] || continue

        while IFS= read -r -d '' target; do
            path="${target#"$CONFIG_DIR/"}"
            [[ -n "${SOURCE_HASHES[$path]+present}" ]] ||
                reconcile_obsolete_file "$path"
        done < <(
            find "$CONFIG_DIR/$root" \
                \( -type d -name '__pycache__' -prune \) -o \
                \( -type f \
                    ! -name '*.pyc' \
                    ! -name '*.pyo' \
                    ! -name '.DS_Store' \
                    -print0 \
                \) -o \
                \( -type l -print0 \)
        )
    done
}

write_state_manifest() {
    [[ "$DRY_RUN" == 0 ]] || return 0
    local temporary path
    temporary="$(mktemp "${STATE_MANIFEST}.XXXXXX")"
    {
        printf 'schema\t1\n'
        printf 'version\t%s\n' "$SOURCE_VERSION"
        printf '%s\n' "${!NEXT_HASHES[@]}" | LC_ALL=C sort | while IFS= read -r path; do
            printf 'file\t%s\t%s\t%s\t%s\n' \
                "$path" "${NEXT_HASHES[$path]}" "${NEXT_OWNERS[$path]}" "${NEXT_VERSIONS[$path]}"
        done
    } > "$temporary"
    chmod 0644 "$temporary"
    mv -f -- "$temporary" "$STATE_MANIFEST"
}

configure_git_identity() {
    [[ "${HOLYCODE_SKIP_GIT_CONFIG:-0}" == 1 ]] && return 0
    local git_user_name="${GIT_USER_NAME:-HolyCode User}"
    local git_user_email="${GIT_USER_EMAIL:-noreply@holycode.local}"
    # safe.directory is a multi-valued setting. Preserve existing entries and
    # add /workspace only when it is not already present.
    if ! runuser -u "$OC_USER" -- git config --global --get-all safe.directory '^/workspace$' >/dev/null 2>&1; then
        runuser -u "$OC_USER" -- git config --global --add safe.directory /workspace
    fi
    runuser -u "$OC_USER" -- git config --global user.name "$git_user_name"
    runuser -u "$OC_USER" -- git config --global user.email "$git_user_email"
    log "configured git as '$git_user_name <$git_user_email>'"
}

if [[ "$DRY_RUN" == 0 ]]; then
    mkdir -p "$CONFIG_DIR" "$STATE_DIR"
    exec 9>"$LOCK_FILE"
    flock -n 9 || die "another bootstrap process is running ($LOCK_FILE)"
fi

LEGACY_SENTINEL="$CONFIG_DIR/.holycode-bootstrapped"
if [[ -e "$LEGACY_SENTINEL" || -L "$LEGACY_SENTINEL" ]]; then
    if [[ "$DRY_RUN" == 1 ]]; then
        log "would remove obsolete first-boot sentinel"
    else
        rm -f -- "$LEGACY_SENTINEL"
        log "removed obsolete first-boot sentinel"
    fi
fi

load_source_manifest
load_previous_manifest

log "reconciling shipped configuration version $SOURCE_VERSION (previous: $PREVIOUS_VERSION)"
for path in "${!SOURCE_HASHES[@]}"; do
    reconcile_current_file "$path"
    [[ "$RECONCILIATION_QUIT" == 0 ]] || exit 0
done
reconcile_unknown_files
[[ "$RECONCILIATION_QUIT" == 0 ]] || exit 0
apply_pending_actions
write_state_manifest

if [[ "$DRY_RUN" == 1 ]]; then
    log "check complete; no files changed"
else
    chown -R "$PUID:$PGID" "$CONFIG_DIR" "$STATE_DIR"
    configure_git_identity
    log "reconciliation complete"
fi
