#!/bin/sh
# Stop the services started by run-server.sh.
# SIGTERM: the mDNS publisher handles it and sends the goodbye before exiting.
DIR=$(cd "$(dirname "$0")/../.." && pwd)
for f in "$DIR"/run/*.pid; do
  [ -e "$f" ] || continue
  pid=$(cat "$f")
  if kill -TERM "$pid" 2>/dev/null; then
    echo "stopped: $(basename "$f" .pid)"
  else
    echo "already stopped: $(basename "$f" .pid)"
  fi
  rm -f "$f"
done
