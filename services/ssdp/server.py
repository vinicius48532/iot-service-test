"""Minimal SSDP server (ssdpy): answers "who is out there?" searches (M-SEARCH).

Não recebe argumentos de linha de comando. Toda a configuração está
dentro do script. O IP local é detectado via ioctl da interface eth0
e o nome do serviço é gerado automaticamente para evitar conflitos de USN.

Responde a buscas SSDP com um LOCATION apontando para um XML de descrição.
"""

import fcntl
import signal
import socket
import struct
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event

from ssdpy import SSDPServer

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# =============================================================================
DEVICE_TYPE = "urn:my-domain:service:myservice:1"
HTTP_PORT = 8000
MAX_AGE = 1800  # segundos de cache para os clientes


def get_interface_ip(ifname="eth0"):
    """Lê o IP de uma interface via ioctl (sem depender de DNS/internet)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(
            fcntl.ioctl(
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack("256s", ifname.encode("utf-8")[:15]),
            )[20:24]
        )
    except OSError:
        return None
    finally:
        try:
            s.close()
        except Exception:
            pass


def get_interface_mac(ifname="eth0"):
    """Lê o endereço MAC de uma interface via ioctl."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(
            s.fileno(),
            0x8927,  # SIOCGIFHWADDR
            struct.pack("256s", ifname.encode("utf-8")[:15]),
        )
        return ":".join("%02x" % b for b in info[18:24])
    except OSError:
        return None
    finally:
        try:
            s.close()
        except Exception:
            pass


ip = get_interface_ip("eth0") or "127.0.0.1"
mac = get_interface_mac("eth0") or "000000000000"

# Nome único baseado no MAC (ou IP como fallback)
if mac:
    SERVICE_NAME = f"server-{mac.replace(':', '')}"
else:
    SERVICE_NAME = f"server-{ip.replace('.', '-')}"

device_id = uuid.uuid5(uuid.NAMESPACE_DNS, SERVICE_NAME)  # único por VM

XML_TEMPLATE = """<?xml version="1.0"?>
<root><device>
  <deviceType>{device_type}</deviceType>
  <friendlyName>{name}</friendlyName>
  <UDN>uuid:{device_id}</UDN>
</device></root>
"""


class Description(BaseHTTPRequestHandler):
    def do_GET(self):  # quem abrir o LOCATION recebe o XML
        self.send_response(200)
        self.send_header("Content-Type", "text/xml")
        self.end_headers()
        xml = XML_TEMPLATE.format(
            device_type=DEVICE_TYPE,
            name=SERVICE_NAME,
            device_id=device_id,
        )
        self.wfile.write(xml.encode())
        self.log_message("XML description served")


def main():
    location = f"http://{ip}:{HTTP_PORT}/description.xml"

    http = HTTPServer(("0.0.0.0", HTTP_PORT), Description)
    http_thread = threading.Thread(target=http.serve_forever, daemon=True)
    http_thread.start()

    server = SSDPServer(
        f"uuid:{device_id}::{DEVICE_TYPE}",  # USN único por VM
        device_type=DEVICE_TYPE,
        address=ip,
        location=location,
        max_age=MAX_AGE,
    )
    ssdp_thread = threading.Thread(target=server.serve_forever, daemon=True)
    ssdp_thread.start()

    print(f"SSDP server for {SERVICE_NAME} at {ip}  (LOCATION {location})")
    print("Press Ctrl+C to stop...")

    stop_event = Event()

    def handle_signal(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while not stop_event.is_set():
            stop_event.wait(0.5)
    finally:
        print("\nShutting down SSDP server...")
        try:
            server.shutdown()
        except Exception:
            pass
        try:
            http.shutdown()
        except Exception:
            pass
        print("Done.")


if __name__ == "__main__":
    main()