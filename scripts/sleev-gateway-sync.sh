#!/bin/bash
# ==============================================================================
# HolyCode - Sleev Gateway Synchronizer
#
# Ensures the persistent gateway layout (~/.local/share/sleev/gateway/) has a
# usable `current` symlink pointing at a valid, executable gateway binary before
# s6-overlay starts. The immutable, build-time-verified image artifact at
# /usr/local/share/holycode/sleev/gateway/<version>/ is authoritative; no
# download happens at startup.
#
# Invoked from scripts/entrypoint.sh as root after UID/GID remapping and
# first-boot bootstrap, but before `exec /init`. Ownership of everything we
# create under the persistent layout is set to the remapped opencode user
# (PUID/PGID) so the s6 `sleev` service (s6-setuidgid opencode) can read it.
#
# Fail-closed: if the desired artifact is unavailable/invalid AND no existing
# persistent `current` gateway is independently usable, we exit non-zero so the
# container refuses to start with a broken gateway.
#
# SECURITY: this script never logs gateway.json, environment secrets, or any
# command argument that could carry credentials. Only paths and versions are
# emitted.
# ==============================================================================
set -euo pipefail

# Image-shipped, build-time-verified artifact (authoritative source).
IMAGE_GATEWAY_ROOT="/usr/local/share/holycode/sleev/gateway"
DESIRED_VERSION="${SLEEV_GATEWAY_VERSION:-}"
if [[ ! "$DESIRED_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "[sleev-gateway-sync] ERROR: invalid SLEEV_GATEWAY_VERSION" >&2
    exit 1
fi
IMAGE_GATEWAY_DIR="${IMAGE_GATEWAY_ROOT}/${DESIRED_VERSION}"
IMAGE_BINARY="${IMAGE_GATEWAY_DIR}/sleeve-gateway"

# Persistent per-user gateway layout consumed by the s6 service.
OC_HOME="/home/opencode"
PERSISTENT_ROOT="${OC_HOME}/.local/share/sleev/gateway"
CURRENT_LINK="${PERSISTENT_ROOT}/current"

# Ownership target (entrypoint remaps opencode to these before invoking us).
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

LEGAL_FILES="LICENSE.md EULA.md THIRD_PARTY_NOTICES.md"

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

# reported_version <bin> -> echo the gateway version token (e.g. "1.6.16").
# Returns non-zero if the binary cannot run or its --version output does not
# contain a "gateway <semver>" line. Emits nothing on failure.
reported_version() {
    local bin="$1"
    local out ver
    out="$("$bin" --version 2>/dev/null)" || return 1
    ver="$(printf '%s\n' "$out" | awk '/^gateway /{print $2; exit}')"
    [ -n "$ver" ] || return 1
    printf '%s\n' "$ver"
}

# current_is_desired -> 0 if `current` resolves to an executable gateway
# already reporting the desired version (idempotent fast path).
current_is_desired() {
    [ -L "$CURRENT_LINK" ] || return 1
    [ -x "$CURRENT_LINK" ] || return 1
    [ "$(reported_version "$CURRENT_LINK")" = "$DESIRED_VERSION" ] || return 1
    return 0
}

# current_is_usable -> 0 if `current` is a well-formed symlink resolving to an
# executable gateway that runs and reports a valid version (any version). Used
# as the fail-closed fallback when the image artifact is unavailable/invalid.
current_is_usable() {
    [ -L "$CURRENT_LINK" ] || return 1
    local target
    target="$(readlink "$CURRENT_LINK")" || return 1
    case "$target" in
        */sleeve-gateway) ;;
        *) return 1 ;;
    esac
    [ -x "$CURRENT_LINK" ] || return 1
    reported_version "$CURRENT_LINK" >/dev/null || return 1
    return 0
}

# image_artifact_ok -> 0 if the build-time image artifact exists, is
# executable, and reports the desired version.
image_artifact_ok() {
    [ -x "$IMAGE_BINARY" ] || return 1
    [ "$(reported_version "$IMAGE_BINARY")" = "$DESIRED_VERSION" ] || return 1
    return 0
}

# sync_from_image -> copies the verified image artifact into a versioned
# persistent dir, validates it, then atomically repoints `current`.
# Never replaces an existing versioned binary in place: we install to a temp
# file and atomically rename within the same directory, then swap the symlink.
sync_from_image() {
    local versioned_dir="${PERSISTENT_ROOT}/${DESIRED_VERSION}"
    local tmp_bin="${versioned_dir}/.sleeve-gateway.tmp"
    local tmp_link="${PERSISTENT_ROOT}/current.tmp"
    local legal src dst

    # Create/reuse the versioned persistent dir with opencode ownership.
    mkdir -p "$versioned_dir"
    chown "$PUID:$PGID" "$PERSISTENT_ROOT" "$versioned_dir"

    # Copy the binary via a temp file so we never clobber a live binary in
    # place. Validate version BEFORE activation.
    install -m 0755 "$IMAGE_BINARY" "$tmp_bin"
    if [ "$(reported_version "$tmp_bin")" != "$DESIRED_VERSION" ]; then
        echo "[sleev-gateway-sync] ERROR: copied gateway failed version validation" >&2
        rm -f "$tmp_bin"
        return 1
    fi
    mv -f "$tmp_bin" "${versioned_dir}/sleeve-gateway"
    chown "$PUID:$PGID" "${versioned_dir}/sleeve-gateway"

    # Copy the legal files (non-secret, restrictive metadata) alongside.
    for legal in $LEGAL_FILES; do
        src="${IMAGE_GATEWAY_DIR}/${legal}"
        if [ -f "$src" ]; then
            dst="${versioned_dir}/${legal}"
            install -m 0644 "$src" "$dst"
            chown "$PUID:$PGID" "$dst"
        fi
    done

    # Re-validate the activated binary before repointing the symlink.
    if [ "$(reported_version "${versioned_dir}/sleeve-gateway")" != "$DESIRED_VERSION" ]; then
        echo "[sleev-gateway-sync] ERROR: activated gateway failed version validation" >&2
        return 1
    fi

    # Atomic symlink swap: create a temp link in the same dir, then rename over
    # `current`. Relative link keeps layout as gateway/<version>/sleeve-gateway.
    rm -f "$tmp_link"
    ln -s "${DESIRED_VERSION}/sleeve-gateway" "$tmp_link"
    mv -Tf "$tmp_link" "$CURRENT_LINK"

    echo "[sleev-gateway-sync] activated gateway ${DESIRED_VERSION}"
    return 0
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
main() {
    # Fast path: current already satisfies the desired version.
    if current_is_desired; then
        echo "[sleev-gateway-sync] gateway already synchronized (${DESIRED_VERSION})"
        return 0
    fi

    if image_artifact_ok; then
        if sync_from_image; then
            return 0
        fi
        # Sync failed - fall through to fail-closed handling.
        echo "[sleev-gateway-sync] WARNING: image sync failed; checking persistent fallback" >&2
    else
        echo "[sleev-gateway-sync] WARNING: desired image artifact unavailable/invalid" >&2
    fi

    # Fail closed unless an existing persistent `current` is independently usable.
    if current_is_usable; then
        echo "[sleev-gateway-sync] WARNING: keeping existing persistent current gateway" >&2
        return 0
    fi

    echo "[sleev-gateway-sync] ERROR: no usable gateway available; refusing to start" >&2
    return 1
}

main "$@"
