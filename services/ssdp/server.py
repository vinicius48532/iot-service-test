"""Minimal SSDP server (ssdpy): answers "who is out there?" searches (M-SEARCH).

Usage:  python server.py <my-ip> <name>      e.g.  python server.py 192.168.10.11 server1
  <my-ip>  IP of this machine on the LAN
  <name>   must be different on every server (it generates the device id)

The answer contains a LOCATION: a URL where a small XML description is served.
"""

import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

from ssdpy import SSDPServer

ip = sys.argv[1]
name = sys.argv[2]

device_type = "urn:my-domain:service:myservice:1"
device_id = uuid.uuid5(uuid.NAMESPACE_DNS, name)  # same name -> same id
location = f"http://{ip}:8000/description.xml"

XML = f"""<?xml version="1.0"?>
<root><device>
  <deviceType>{device_type}</deviceType>
  <friendlyName>{name}</friendlyName>
  <UDN>uuid:{device_id}</UDN>
</device></root>
"""


class Description(BaseHTTPRequestHandler):
    def do_GET(self):  # anyone who opens the LOCATION gets the XML
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.end_headers()
        self.wfile.write(XML.encode())


# serve the XML in the background...
http = HTTPServer(("0.0.0.0", 8000), Description)
threading.Thread(target=http.serve_forever, daemon=True).start()

# ...and answer SSDP searches in the foreground
server = SSDPServer(
    f"uuid:{device_id}::{device_type}",  # unique service name (USN)
    device_type=device_type,
    address=ip,                          # use the LAN interface
    location=location,
    max_age=1800,                        # how long clients may cache the answer (s)
)
print(f"SSDP server for {name} at {ip}  (LOCATION {location})")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
