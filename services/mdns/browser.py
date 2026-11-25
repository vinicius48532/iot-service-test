"""Minimal mDNS browser (zeroconf): encontra serviços anunciados na rede local.

Não recebe argumentos de linha de comando. Toda a configuração está dentro
do script. O IP local é detectado via ioctl da interface eth0 (útil em QEMU/GNS3).

Use Ctrl+C para parar antes do tempo limite.
"""

import fcntl
import signal
import socket
import struct
from threading import Event

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# =============================================================================
SERVICE_TYPE = "_myservice._tcp.local."
LISTEN_SECONDS = 15  # tempo de escuta em segundos


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


class Listener(ServiceListener):
    def add_service(self, zc, service_type, name):  # um serviço apareceu
        info = zc.get_service_info(service_type, name)  # pede os detalhes
        if info is not None:
            addresses = info.parsed_addresses()
            addr_str = ", ".join(addresses) if addresses else "?"
            print(f"FOUND   {name}  {addr_str}:{info.port}  {info.properties}")
        else:
            print(f"FOUND   {name}  (no details)")

    def remove_service(self, zc, service_type, name):  # um serviço se despediu
        print(f"REMOVED {name}")

    def update_service(self, zc, service_type, name):  # obrigatório, não usado aqui
        pass


def main():
    ip = get_interface_ip("eth0") or "127.0.0.1"
    print(f"mDNS browser listening on interface IP: {ip}")
    print(f"Browsing for {SERVICE_TYPE} for {LISTEN_SECONDS} seconds...")
    print("Press Ctrl+C to stop early.\n")

    zc = Zeroconf()
    listener = Listener()
    ServiceBrowser(zc, SERVICE_TYPE, listener)

    stop_event = Event()

    def handle_signal(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        stop_event.wait(LISTEN_SECONDS)
    finally:
        print("\nClosing mDNS browser...")
        zc.close()
        print("Done.")


if __name__ == "__main__":
    main()