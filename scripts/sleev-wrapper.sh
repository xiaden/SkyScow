#!/bin/bash
# ------------------------------------------------------------------
# HolyCode sleev wrapper – runs the selected Sleev CLI with tolerant exit
# handling.
#
# Gateway synchronization and supervision are owned elsewhere:
#   - scripts/sleev-gateway-sync.sh (invoked from entrypoint before s6
#     starts) guarantees gateway/current is valid, and
#   - s6-overlay runs the gateway binary directly via the `sleev` run
#     script.
#
# This wrapper therefore does NOT trigger s6 or manage the gateway. The
# synchronizer selects both CLI and gateway before s6 starts. The selected CLI
# still tries to manage the gateway via systemd (which does not exist in
# containers), so we tolerate that failure while the S6 service remains the
# gateway supervisor.
# ------------------------------------------------------------------

# Let the selected CLI do its setup (write config, auth, etc.).
# It will probably fail trying to manage the gateway via systemd, and
# that is expected inside a container – capture the exit code but do
# NOT abort the script.
cli_bin="/home/opencode/.local/share/sleev/cli/current"
if [ ! -x "$cli_bin" ]; then
  echo "sleev CLI is unavailable; container startup synchronization did not complete" >&2
  exit 127
fi
set +e
"$cli_bin" "$@"
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
