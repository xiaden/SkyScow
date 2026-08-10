#!/bin/bash
# ------------------------------------------------------------------
# HolyCode sleev wrapper – runs the real sleev CLI with tolerant exit
# handling.
#
# Gateway synchronization and supervision are owned elsewhere:
#   - scripts/sleev-gateway-sync.sh (invoked from entrypoint before s6
#     starts) guarantees gateway/current is valid, and
#   - s6-overlay runs the gateway binary directly via the `sleev` run
#     script.
#
# This wrapper therefore does NOT trigger s6, download a gateway, or
# replace the authoritative build-time gateway. It is purely CLI
# passthrough. The real CLI tries to manage the gateway via systemd
# (which does not exist in containers), so we tolerate its failure as
# long as the gateway binary ends up on disk.
# ------------------------------------------------------------------

# Let the real CLI do its setup (download binary, write config, etc.).
# It will probably fail trying to manage the gateway via systemd, and
# that is expected inside a container – capture the exit code but do
# NOT abort the script.
set +e
/usr/local/bin/sleev.real "$@"
real_exit=$?
set -e

# If the gateway binary exists (was already there or just installed),
# treat the invocation as successful – s6 has the process from here.
gateway_bin="/home/opencode/.local/share/sleev/gateway/current"
if [ -x "$gateway_bin" ]; then
  exit 0
fi

# Gateway binary does not exist and the real CLI failed; propagate
# the failure so OpenCode knows something is wrong.
exit $real_exit
