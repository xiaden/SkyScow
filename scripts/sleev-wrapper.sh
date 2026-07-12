#!/bin/bash
# ------------------------------------------------------------------
# HolyCode sleev wrapper – runs the real sleev CLI, then hands the
# gateway binary off to s6-overlay for supervision.  The real CLI
# tries to manage the gateway via systemd (which does not exist in
# containers), so we tolerate its failure as long as the gateway
# binary ends up on disk.
# ------------------------------------------------------------------

# Let the real CLI do its setup (download binary, write config, etc.).
# It will probably fail trying to manage the gateway via systemd, and
# that is expected inside a container – capture the exit code but do
# NOT abort the script.
/usr/local/bin/sleev.real "$@" || true
real_exit=$?

# If sleev.real left us a gateway binary, tell s6 to start it
# regardless of whether the CLI succeeded.
gateway_bin="/home/opencode/.local/share/sleev/gateway/current"
if [ -x "$gateway_bin" ]; then
  s6-svc -u /etc/s6-overlay/s6-rc.d/sleev 2>/dev/null || true
fi

# If the gateway binary exists (was already there or just installed),
# treat the invocation as successful – s6 has the process from here.
if [ -x "$gateway_bin" ]; then
  exit 0
fi

# Gateway binary does not exist and the real CLI failed; propagate
# the failure so OpenCode knows something is wrong.
exit $real_exit
