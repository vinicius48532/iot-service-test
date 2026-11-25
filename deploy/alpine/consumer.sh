#!/bin/sh
# Discover the servers from the consumer node.
# Usage: [PROTO=all|coap|mdns|ssdp] ./consumer.sh <consumer-ip> [server-ip ...]
#   e.g.: PROTO=mdns ./consumer.sh 192.168.10.10
#         PROTO=coap ./consumer.sh 192.168.10.10 192.168.10.11 192.168.10.12
# The 1st argument is the consumer's OWN LAN IP. The server IPs are only used by
# CoAP (it does not discover anything by itself); SSDP and mDNS find the servers alone.
set -eu
[ $# -ge 1 ] || { echo "usage: [PROTO=...] $0 <consumer-ip> [server-ip ...]"; exit 1; }
IP=$1; shift
PROTO=${PROTO:-all}
case $PROTO in all|coap|mdns|ssdp) ;; *) echo "PROTO must be all, coap, mdns or ssdp"; exit 1;; esac
if { [ "$PROTO" = all ] || [ "$PROTO" = coap ]; } && [ $# -eq 0 ]; then
  echo "CoAP needs the server IPs: $0 <consumer-ip> <server-ip> [...]"; exit 1
fi
DIR=$(cd "$(dirname "$0")/../.." && pwd)
PY=$DIR/.venv/bin/python
cd "$DIR"
# Without IPv6 in the kernel, use aiocoap's IPv4 client transport
[ -e /proc/net/if_inet6 ] || export AIOCOAP_CLIENT_TRANSPORT=simple6

want() { [ "$PROTO" = all ] || [ "$PROTO" = "$1" ]; }

if want ssdp; then
  echo "##### SSDP"; "$PY" services/ssdp/client.py "$IP"
fi
if want mdns; then
  echo; echo "##### mDNS"; "$PY" services/mdns/browser.py "$IP" 5
fi
if want coap; then
  for S in "$@"; do
    echo; echo "##### CoAP $S"
    "$PY" services/coap/client.py "$S"
  done
fi
