#!/bin/sh
# Install Python and the libraries into a local venv (run ONCE per node, needs internet).
set -eu
DIR=$(cd "$(dirname "$0")/../.." && pwd)
apk add --no-cache python3 py3-pip
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install --no-cache-dir aiocoap zeroconf ssdpy
echo "OK: venv at $DIR/.venv"
