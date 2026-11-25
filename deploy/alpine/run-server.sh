#!/bin/sh
# Start the services in the background.
# Usage: [PROTO=all|coap|mdns|ssdp] ./run-server.sh <LAN-IP> <unique-name>
#   e.g.: PROTO=ssdp ./run-server.sh 192.168.10.11 server1
# PROTO (default: all) lets you test one protocol at a time.
set -eu
[ $# -eq 2 ] || { echo "usage: [PROTO=all|coap|mdns|ssdp] $0 <lan-ip> <unique-name>"; exit 1; }
IP=$1; NAME=$2
PROTO=${PROTO:-all}
case $PROTO in all|coap|mdns|ssdp) ;; *) echo "PROTO must be all, coap, mdns or ssdp"; exit 1;; esac
DIR=$(cd "$(dirname "$0")/../.." && pwd)
PY=$DIR/.venv/bin/python
LOGS=$DIR/logs; RUN=$DIR/run; mkdir -p "$LOGS" "$RUN"
cd "$DIR"

want() { [ "$PROTO" = all ] || [ "$PROTO" = "$1" ]; }

# CoAP listens on "::" (IPv4 + IPv6). Without IPv6 in the kernel, bind to the IP instead
# (aiocoap's IPv4 transport, which has no CoAP multicast).
COAP_HOST="::"
if [ ! -e /proc/net/if_inet6 ]; then
  COAP_HOST="$IP"
  export AIOCOAP_SERVER_TRANSPORT=simplesocketserver
fi

start() { # $1=name  rest=command
  n=$1; shift
  nohup "$@" >"$LOGS/$n.log" 2>&1 &
  echo $! > "$RUN/$n.pid"
  echo "  $n  pid=$!"
}

echo "Server $NAME at $IP (PROTO=$PROTO)"
if want coap; then
  start coap env PYTHONUNBUFFERED=1 "$PY" services/coap/server.py "$COAP_HOST"
fi
if want mdns; then
  start mdns env PYTHONUNBUFFERED=1 "$PY" services/mdns/publisher.py "$IP" "$NAME"
fi
if want ssdp; then
  start ssdp env PYTHONUNBUFFERED=1 "$PY" services/ssdp/server.py "$IP" "$NAME"
fi
echo "Logs in $LOGS"
