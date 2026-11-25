"""Minimal mDNS browser (zeroconf): encontra serviços anunciados na rede local.

Não recebe argumentos de linha de comando. Toda a configuração está dentro
do script. O IP local é detectado automaticamente (útil em QEMU/GNS3).

Use Ctrl+C para parar antes do tempo limite.
"""

import signal
import socket
from threading import Event

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# =============================================================================
SERVICE_TYPE = "_myservice._tcp.local."
LISTEN_SECONDS = 15  # tempo de escuta em segundos


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
    ip = get_local_ip()
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
        # Aguarda o tempo configurado ou até o usuário interromper
        stop_event.wait(LISTEN_SECONDS)
    finally:
        print("\nClosing mDNS browser...")
        zc.close()
        print("Done.")


if __name__ == "__main__":
    main()
