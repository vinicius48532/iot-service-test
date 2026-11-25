"""Minimal SSDP client (ssdpy): busca dispositivos e lê a descrição.

Não recebe argumentos de linha de comando. Toda a configuração está
dentro do script. O IP local é detectado via ioctl da interface eth0.

Envia múltiplas buscas M-SEARCH e aguarda respostas de todos os
dispositivos na rede.
"""

import fcntl
import socket
import struct
import time
import urllib.request

from ssdpy import SSDPClient

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# =============================================================================
SEARCH_TIMEOUT = 5        # tempo total de espera por respostas (segundos)
XML_TIMEOUT = 3           # segundos para baixar o XML de descrição
NUM_SEARCHES = 3          # quantas buscas M-SEARCH enviar
SEARCH_INTERVAL = 1       # intervalo entre buscas (segundos)


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


def main():
    ip = get_interface_ip("eth0") or "127.0.0.1"

    client = SSDPClient(address=ip, timeout=SEARCH_TIMEOUT)
    # envia a busca multicast pela interface LAN
    client.sock.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_MULTICAST_IF,
        socket.inet_aton(ip),
    )

    print(f"Buscando dispositivos SSDP na interface {ip}...")
    print(f"Enviando {NUM_SEARCHES} busca(s) M-SEARCH...\n")

    devices = {}  # usn -> device

    for i in range(NUM_SEARCHES):
        print(f"  Busca {i + 1}/{NUM_SEARCHES}...")
        try:
            answers = client.m_search("ssdp:all")
            for a in answers:
                usn = a.get("usn", "N/A")
                if usn not in devices:
                    devices[usn] = a
                    print(f"    [+] Novo dispositivo: {usn}")
                    print(f"        LOCATION: {a.get('location', 'N/A')}")
        except Exception as e:
            print(f"    Erro na busca {i + 1}: {e}")

        if i < NUM_SEARCHES - 1:
            time.sleep(SEARCH_INTERVAL)

    print(f"\n{len(devices)} dispositivo(s) encontrado(s)\n")

    for usn, device in devices.items():
        location = device.get("location", "N/A")
        print(f"USN:      {usn}")
        print(f"LOCATION: {location}")
        try:
            xml = urllib.request.urlopen(location, timeout=XML_TIMEOUT).read().decode()
            print(xml)
        except Exception as e:
            print(f"Erro ao baixar descrição de {location}: {e}")
        print("-" * 40)


if __name__ == "__main__":
    main()