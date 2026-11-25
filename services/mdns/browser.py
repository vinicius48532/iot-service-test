"""Minimal mDNS browser (zeroconf): finds services announced on the local network.

Usage:  python browser.py <my-ip> [seconds]     e.g.  python browser.py 192.168.10.10 5
  <my-ip>    IP of this machine on the LAN
  [seconds]  how long to listen (default 5); use a large value to watch services leave
"""

import sys
import time

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

ip = sys.argv[1]
seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 5


class Listener(ServiceListener):
    def add_service(self, zc, service_type, name):       # a service appeared
        info = zc.get_service_info(service_type, name)   # ask for its details
        print(f"FOUND   {name}  {info.parsed_addresses()}:{info.port}  {info.properties}")

    def remove_service(self, zc, service_type, name):    # a service said goodbye
        print(f"REMOVED {name}")

    def update_service(self, zc, service_type, name):    # required, unused here
        pass


zc = Zeroconf(interfaces=[ip])
ServiceBrowser(zc, "_myservice._tcp.local.", Listener())
time.sleep(seconds)
zc.close()
