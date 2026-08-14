#!/bin/bash
# ==============================================================================
# HolyCode - Sleev version synchronizer
#
# Selects one complete Sleev release for the persistent volume before s6 starts:
#   - the CLI at ~/.local/share/sleev/cli/current/sleev
#   - the gateway at ~/.local/share/sleev/gateway/current
#
# The image's pinned release is available without network access. If SLEEV_VERSION
# requests another release, both official artifacts are downloaded, checked, and
# installed before either current symlink is changed.
#
# Invoked as root from entrypoint.sh after UID/GID remapping. No credentials or
# gateway configuration contents are printed. An explicit version failure is
# fatal; an older installed release is never selected as a silent fallback.
# ==============================================================================
set -euo pipefail

RELEASE_BASE="https://storage.googleapis.com/sleeve-releases"
DESIRED_VERSION="${SLEEV_VERSION:-}"
if [[ ! "$DESIRED_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "[sleev-sync] ERROR: SLEEV_VERSION must be a stable semver" >&2
    exit 1
fi

OC_HOME="/home/opencode"
SLEEV_ROOT="${OC_HOME}/.local/share/sleev"
CLI_ROOT="${OC_HOME}/.local/share/sleev/cli"
GATEWAY_ROOT="${OC_HOME}/.local/share/sleev/gateway"
CLI_CURRENT="${CLI_ROOT}/current"
GATEWAY_CURRENT="${GATEWAY_ROOT}/current"
PACKAGED_GATEWAY="/usr/local/share/holycode/sleev/gateway/packaged/sleeve-gateway"
PACKAGED_CLI="/usr/local/bin/sleev.real"
PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
LEGAL_FILES=(LICENSE.md EULA.md THIRD_PARTY_NOTICES.md)

case "$(uname -m)" in
    x86_64|amd64) PLATFORM="linux-x64" ;;
    aarch64|arm64) PLATFORM="linux-arm64" ;;
    *)
        echo "[sleev-sync] ERROR: unsupported runtime architecture $(uname -m)" >&2
        exit 1
        ;;
esac

reported_cli_version() {
    local bin="$1" output version
    output="$($bin --version 2>/dev/null)" || return 1
    version="$(printf '%s\n' "$output" | awk '/^[0-9]+\.[0-9]+\.[0-9]+$/{print; exit}')"
    [ -n "$version" ] || return 1
    printf '%s\n' "$version"
}

reported_gateway_version() {
    local bin="$1" output version
    output="$($bin --version 2>/dev/null)" || return 1
    version="$(printf '%s\n' "$output" | awk '/^gateway [0-9]+\.[0-9]+\.[0-9]+$/{print $2; exit}')"
    [ -n "$version" ] || return 1
    printf '%s\n' "$version"
}

valid_current() {
    [ -L "$CLI_CURRENT" ] && [ -x "$CLI_CURRENT" ] || return 1
    [ -L "$GATEWAY_CURRENT" ] && [ -x "$GATEWAY_CURRENT" ] || return 1
    [ "$(reported_cli_version "$CLI_CURRENT")" = "$DESIRED_VERSION" ] || return 1
    [ "$(reported_gateway_version "$GATEWAY_CURRENT")" = "$DESIRED_VERSION" ] || return 1
}

read_manifest_artifact() {
    local kind="$1" manifest="$2" expected_name="$3" metadata
    metadata="$(python3 - "$manifest" "$kind" "$DESIRED_VERSION" "$PLATFORM" "$expected_name" "$RELEASE_BASE" <<'PY'
import json
import re
import sys

manifest_path, kind, version, platform, expected_name, release_base = sys.argv[1:]
with open(manifest_path, encoding="utf-8") as handle:
    manifest = json.load(handle)

if manifest.get("version") != version:
    raise SystemExit("manifest version mismatch")
artifact = manifest.get("artifacts", {}).get(platform)
if not isinstance(artifact, dict):
    raise SystemExit("manifest has no artifact for this platform")

url = artifact.get("url")
expected_url = f"{release_base}/{kind}/{version}/{expected_name}"
if url != expected_url or not url.startswith("https://"):
    raise SystemExit("manifest artifact URL is not the pinned official URL")

sha256 = artifact.get("sha256")
if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
    raise SystemExit("manifest contains an invalid SHA-256")
size = artifact.get("size")
if not isinstance(size, int) or size <= 0:
    raise SystemExit("manifest contains an invalid artifact size")

print(url, sha256, size)
PY
)" || return 1
    printf '%s\n' "$metadata"
}

download_artifact() (
    set -euo pipefail
    local kind="$1" archive_name="$2" output_dir="$3"
    local work manifest url sha256 size archive extracted binary installed_name

    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT
    manifest="$work/manifest.json"
    archive="$work/$archive_name"
    extracted="$work/extracted"
    mkdir "$extracted"

    curl -fsSL --proto '=https' --tlsv1.2 \
        -o "$manifest" \
        "${RELEASE_BASE}/${kind}/${DESIRED_VERSION}/manifest.json"
    read -r url sha256 size < <(
        read_manifest_artifact "$kind" "$manifest" "$archive_name"
    )
    [ -n "$url" ] && [ -n "$sha256" ] && [ -n "$size" ]

    curl -fsSL --proto '=https' --tlsv1.2 -o "$archive" "$url"
    [ "$(stat -c '%s' "$archive")" -eq "$size" ] || {
        echo "[sleev-sync] ERROR: $kind archive size mismatch" >&2
        return 1
    }
    printf '%s  %s\n' "$sha256" "$archive" | sha256sum -c - >/dev/null

    tar -xzf "$archive" -C "$extracted"
    if [ "$kind" = cli ]; then
        binary="${extracted}/sleev"
        installed_name="sleev"
    else
        binary="${extracted}/sleeve-gateway-${PLATFORM}"
        installed_name="sleeve-gateway"
    fi
    [ -x "$binary" ] || {
        echo "[sleev-sync] ERROR: $kind archive has no executable" >&2
        return 1
    }

    if [ "$kind" = cli ]; then
        [ "$(reported_cli_version "$binary")" = "$DESIRED_VERSION" ] || return 1
    else
        [ "$(reported_gateway_version "$binary")" = "$DESIRED_VERSION" ] || return 1
    fi

    mkdir -p "$output_dir"
    install -m 0755 "$binary" "${output_dir}/${installed_name}"
    for legal in "${LEGAL_FILES[@]}"; do
        [ -f "${extracted}/${legal}" ] || continue
        install -m 0644 "${extracted}/${legal}" "${output_dir}/${legal}"
    done
)

install_packaged_release() {
    local cli_dir="${CLI_ROOT}/${DESIRED_VERSION}"
    local gateway_dir="${GATEWAY_ROOT}/${DESIRED_VERSION}"
    local legal source

    [ -x "$PACKAGED_CLI" ] || return 1
    [ "$(reported_cli_version "$PACKAGED_CLI")" = "$DESIRED_VERSION" ] || return 1
    [ -x "$PACKAGED_GATEWAY" ] || return 1
    [ "$(reported_gateway_version "$PACKAGED_GATEWAY")" = "$DESIRED_VERSION" ] || return 1

    mkdir -p "$cli_dir" "$gateway_dir"
    install -m 0755 "$PACKAGED_CLI" "${cli_dir}/sleev"
    install -m 0755 "$PACKAGED_GATEWAY" "${gateway_dir}/sleeve-gateway"

    for legal in "${LEGAL_FILES[@]}"; do
        for source in \
            "/usr/local/lib/node_modules/sleev/${legal}" \
            "/usr/local/share/holycode/sleev/gateway/packaged/${legal}"; do
            if [ -f "$source" ]; then
                install -m 0644 "$source" "${gateway_dir}/${legal}"
                install -m 0644 "$source" "${cli_dir}/${legal}"
                break
            fi
        done
    done
}

activate_release() {
    local cli_dir="${CLI_ROOT}/${DESIRED_VERSION}"
    local gateway_dir="${GATEWAY_ROOT}/${DESIRED_VERSION}"
    local cli_tmp gateway_tmp old_cli old_gateway

    [ "$(reported_cli_version "${cli_dir}/sleev")" = "$DESIRED_VERSION" ] || return 1
    [ "$(reported_gateway_version "${gateway_dir}/sleeve-gateway")" = "$DESIRED_VERSION" ] || return 1

    chown -R "$PUID:$PGID" "$cli_dir" "$gateway_dir"
    chown "$PUID:$PGID" "$SLEEV_ROOT" "$CLI_ROOT" "$GATEWAY_ROOT"

    cli_tmp="${CLI_ROOT}/current.tmp"
    gateway_tmp="${GATEWAY_ROOT}/current.tmp"
    old_cli="$(readlink "$CLI_CURRENT" 2>/dev/null || true)"
    old_gateway="$(readlink "$GATEWAY_CURRENT" 2>/dev/null || true)"
    rm -f "$cli_tmp" "$gateway_tmp"
    ln -s "${DESIRED_VERSION}/sleev" "$cli_tmp"
    ln -s "${DESIRED_VERSION}/sleeve-gateway" "$gateway_tmp"
    mv -Tf "$cli_tmp" "$CLI_CURRENT"
    if ! mv -Tf "$gateway_tmp" "$GATEWAY_CURRENT"; then
        rm -f "$CLI_CURRENT"
        [ -n "$old_cli" ] && ln -s "$old_cli" "$CLI_CURRENT"
        [ -n "$old_gateway" ] && ln -s "$old_gateway" "$GATEWAY_CURRENT"
        return 1
    fi
    echo "[sleev-sync] activated Sleev ${DESIRED_VERSION} (${PLATFORM})"
}

main() {
    mkdir -p "$CLI_ROOT" "$GATEWAY_ROOT"
    # The gateway runs as opencode and tightens this directory to 0700 during
    # startup. Establish ownership before s6 starts so that chmod succeeds,
    # including when a native-Linux bind mount was created by root.
    chown -R "$PUID:$PGID" "$SLEEV_ROOT"
    chmod 0700 "$SLEEV_ROOT"

    if valid_current; then
        echo "[sleev-sync] Sleev ${DESIRED_VERSION} already active"
        return 0
    fi

    # The image-shipped artifacts are used only when they report the requested
    # version. Any other requested version must be fetched and verified.
    if [ "$(reported_cli_version "$PACKAGED_CLI" 2>/dev/null || true)" = "$DESIRED_VERSION" ]; then
        install_packaged_release || {
            echo "[sleev-sync] ERROR: packaged Sleev ${DESIRED_VERSION} failed validation" >&2
            exit 1
        }
    else
        download_artifact cli "sleev-${PLATFORM}.tar.gz" "${CLI_ROOT}/${DESIRED_VERSION}"
        download_artifact gateway "sleeve-gateway-${PLATFORM}.tar.gz" "${GATEWAY_ROOT}/${DESIRED_VERSION}"
    fi

    activate_release || {
        echo "[sleev-sync] ERROR: Sleev ${DESIRED_VERSION} failed activation" >&2
        exit 1
    }
}

main "$@"
