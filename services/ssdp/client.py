"""Minimal SSDP client (ssdpy): busca dispositivos e lê a descrição.

Não recebe argumentos de linha de comando. Toda a configuração está
dentro do script. O IP local é detectado automaticamente (útil em QEMU/GNS3).
"""

import socket
import urllib.request

from ssdpy import SSDPClient

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# =============================================================================
SEARCH_TIMEOUT = 3   # segundos de espera por respostas
XML_TIMEOUT = 3      # segundos para baixar o XML de descrição


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

    client = SSDPClient(address=ip, timeout=SEARCH_TIMEOUT)
    # envia a busca multicast pela interface LAN
    client.sock.setsockopt(
        socket.IPPROTO_IP,
        socket.IP_MULTICAST_IF,
        socket.inet_aton(ip),
    )

    print(f"Buscando dispositivos SSDP na interface {ip}...")
    answers = client.m_search("ssdp:all")  # "everybody, answer me!"
    devices = {a["usn"]: a for a in answers}  # uma entrada por dispositivo

    print(f"{len(devices)} dispositivo(s) encontrado(s)\n")

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
