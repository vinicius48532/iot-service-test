"""Minimal mDNS publisher (zeroconf): anuncia um serviço na rede local.

Não recebe argumentos de linha de comando. Toda a configuração está dentro
do script. O IP local é detectado automaticamente (útil em QEMU/GNS3).

Use Ctrl+C para parar: o serviço é removido da rede antes de encerrar.
"""

import signal
import socket
from threading import Event

from zeroconf import ServiceInfo, Zeroconf

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# =============================================================================
SERVICE_TYPE = "_myservice._tcp.local."
SERVICE_NAME = "server1"              # deve ser diferente em cada servidor
PORT = 8080
PROPERTIES = {"version": "1.0"}


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


def main():
    ip = get_local_ip()
    name = SERVICE_NAME

    info = ServiceInfo(
        SERVICE_TYPE,
        f"{name}.{SERVICE_TYPE}",
        addresses=[socket.inet_aton(ip)],
        port=PORT,
        properties=PROPERTIES,
        server=f"{name}.local.",
    )

    zc = Zeroconf()
    zc.register_service(info)
    print(f"Published {name}.{SERVICE_TYPE} at {ip}:{PORT}")
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
        print("\nUnpublishing service...")
        try:
            zc.unregister_service(info)
        except Exception:
            pass
        zc.close()
        print("Done.")


if __name__ == "__main__":
    main()
