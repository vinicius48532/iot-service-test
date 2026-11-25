"""Minimal mDNS publisher (zeroconf): anuncia um serviço na rede local.

Não recebe argumentos de linha de comando. Toda a configuração está dentro
do script. O IP local é detectado via ioctl da interface eth0 e o nome do
serviço é gerado automaticamente a partir do MAC, evitando conflitos entre
múltiplas VMs.

Use Ctrl+C para parar: o serviço é removido da rede antes de encerrar.
"""

import fcntl
import signal
import socket
import struct
from threading import Event

from zeroconf import ServiceInfo, Zeroconf

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# =============================================================================
SERVICE_TYPE = "_myservice._tcp.local."
PORT = 8080
PROPERTIES = {"version": "1.0"}


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


def main():
    info = ServiceInfo(
        SERVICE_TYPE,
        f"{SERVICE_NAME}.{SERVICE_TYPE}",
        addresses=[socket.inet_aton(ip)],
        port=PORT,
        properties=PROPERTIES,
        server=f"{SERVICE_NAME}.local.",
    )

    zc = Zeroconf()
    zc.register_service(info)
    print(f"Published {SERVICE_NAME}.{SERVICE_TYPE} at {ip}:{PORT}")
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