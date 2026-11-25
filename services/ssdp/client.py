"""Minimal SSDP client (ssdpy): searches for devices and reads their description.

Usage:  python client.py <my-ip>      e.g.  python client.py 192.168.10.10
  <my-ip>  IP of this machine on the LAN
"""

import socket
import sys
import urllib.request

from ssdpy import SSDPClient

ip = sys.argv[1]

client = SSDPClient(address=ip, timeout=3)  # waits up to 3 s for answers
# send the multicast search out of the LAN interface
client.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ip))

answers = client.m_search("ssdp:all")             # "everybody, answer me!"
devices = {a["usn"]: a for a in answers}          # one entry per device

print(f"{len(devices)} device(s) found")
for usn, device in devices.items():
    print(f"USN:      {usn}")
    print(f"LOCATION: {device['location']}")
    xml = urllib.request.urlopen(device["location"], timeout=3).read().decode()
    print(xml)
