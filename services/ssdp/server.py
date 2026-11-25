"""Minimal SSDP server (ssdpy): answers "who is out there?" searches (M-SEARCH).

Não recebe argumentos de linha de comando. Toda a configuração está
dentro do script. O IP local é detectado automaticamente (útil em QEMU/GNS3).

Responde a buscas SSDP com um LOCATION apontando para um XML de descrição.
"""

import signal
import socket
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event

from ssdpy import SSDPServer

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# =============================================================================
SERVICE_NAME = "server1"              # deve ser diferente em cada servidor
DEVICE_TYPE = "urn:my-domain:service:myservice:1"
HTTP_PORT = 8000
MAX_AGE = 1800                        # segundos de cache para os clientes


def get_local_ip():
    """Detecta o endereço IP local da máquina (melhor esforço, sem internet)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("8.8.8.8", 53))  # não envia pacote, apenas escolhe a interface
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


device_id = uuid.uuid5(uuid.NAMESPACE_DNS, SERVICE_NAME)  # mesmo nome -> mesmo id

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


def main():
    ip = get_local_ip()
    location = f"http://{ip}:{HTTP_PORT}/description.xml"

    # Servidor HTTP para o XML (segundo plano)
    http = HTTPServer(("0.0.0.0", HTTP_PORT), Description)
    http_thread = threading.Thread(target=http.serve_forever, daemon=True)
    http_thread.start()

    # Servidor SSDP para responder buscas (segundo plano, para permitir sinal)
    server = SSDPServer(
        f"uuid:{device_id}::{DEVICE_TYPE}",  # USN único
        device_type=DEVICE_TYPE,
        address=ip,                          # interface LAN
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
