"""Minimal mDNS publisher (zeroconf): announces a service on the local network.

Usage:  python publisher.py <my-ip> <name>      e.g.  python publisher.py 192.168.10.11 server1
  <my-ip>  IP of this machine on the LAN
  <name>   must be different on every server
Stop it with Ctrl+C (or SIGTERM): it tells the network that the service is gone.
"""

import signal
import socket
import sys
import time

from zeroconf import ServiceInfo, Zeroconf

ip = sys.argv[1]
name = sys.argv[2]
service_type = "_myservice._tcp.local."

info = ServiceInfo(
    service_type,
    f"{name}.{service_type}",             # instance name: server1._myservice._tcp.local.
    addresses=[socket.inet_aton(ip)],     # where the service is...
    port=8080,                            # ...and on which port
    properties={"version": "1.0"},        # extra data (TXT record)
    server=f"{name}.local.",              # host name: server1.local.
)

zc = Zeroconf(interfaces=[ip])            # use only the LAN interface
zc.register_service(info)
print(f"Published {name}.{service_type} at {ip}:8080")

# Turn Ctrl+C / SIGTERM into a normal exit, so the cleanup below always runs.
signal.signal(signal.SIGINT, lambda *args: sys.exit(0))
signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))

try:
    while True:
        time.sleep(1)
finally:
    zc.unregister_service(info)           # sends the "goodbye"
    zc.close()
