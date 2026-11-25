"""Minimal CoAP server (aiocoap) — descoberta automática de serviços.

Ambiente: QEMU + GNS3. Sem dependência de internet.
Não recebe argumentos de linha de comando.

Recursos:
  /.well-known/core  -> listagem de serviços (descoberta CoAP RFC 6690)
  /time              -> hora atual em UTC
  /sensor            -> temperatura simulada; suporta CoAP Observe

Descoberta multicast: socket UDP separado em 224.0.1.187:5684 (thread isolada)
responde a requisições de descoberta com o link format dos recursos.
"""

import asyncio
import fcntl
import random
import signal
import socket
import struct
import threading
from datetime import datetime, timezone

import aiocoap
import aiocoap.resource as resource
from aiocoap import Code, Message

HOST = "0.0.0.0"
PORT = 5683
MCAST_GROUP = "224.0.1.187"   # All CoAP Nodes (RFC 7390)
MCAST_DISCOVERY_PORT = 5684   # Porta dedicada para descoberta multicast


def get_interface_ip(ifname="eth0"):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(
            fcntl.ioctl(
                s.fileno(),
                0x8915,
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


class Time(resource.Resource):
    async def render_get(self, request):
        now = datetime.now(timezone.utc).isoformat()
        return Message(code=Code.CONTENT, payload=now.encode(), content_format=0)

    def get_link_description(self, request=None):
        return {"rt": "time.core", "if": "core.time", "title": "Local time"}


class Sensor(resource.ObservableResource):
    def __init__(self):
        super().__init__()
        self.value = 25.0
        self._task = None

    def start(self):
        if self._task is None:
            self._task = asyncio.get_running_loop().create_task(self.update_forever())

    async def update_forever(self):
        try:
            while True:
                await asyncio.sleep(1)
                self.value = round(random.uniform(20, 30), 2)
                self.updated_state()
        except asyncio.CancelledError:
            pass

    async def render_get(self, request):
        return Message(code=Code.CONTENT, payload=str(self.value).encode(), content_format=0)

    def stop(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def get_link_description(self, request=None):
        return {"rt": "temperature.sensor", "if": "sensor.single", "title": "Ambient temperature"}


def build_link_format():
    links = [
        "</.well-known/core>",
        '</time>;rt="time.core";if="core.time";title="Local time"',
        '</sensor>;rt="temperature.sensor";if="sensor.single";title="Ambient temperature"',
    ]
    return ", ".join(links).encode()


def multicast_discovery_thread(local_ip, stop_event):
    """Thread separada para descoberta multicast (sem asyncio)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    except (AttributeError, OSError):
        pass

    sock.bind(("0.0.0.0", MCAST_DISCOVERY_PORT))

    group = socket.inet_aton(MCAST_GROUP)
    iface = socket.inet_aton(local_ip)
    membership = group + iface
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(1.0)

    print(f"[Multicast] Servidor entrou no grupo {MCAST_GROUP}:{MCAST_DISCOVERY_PORT} na interface {local_ip}")

    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(2048)
        except socket.timeout:
            continue
        except OSError:
            break

        if len(data) < 4:
            continue
        if data[0] == 0x40 and data[1] == 0x01:
            payload_str = data.decode(errors="ignore")
            if "well-known" in payload_str and "core" in payload_str:
                print(f"[Multicast] Descoberta recebida de {addr}")
                response = build_link_format()
                msg_id = 0x5678
                header = bytes([0x50, 0x45, (msg_id >> 8) & 0xFF, msg_id & 0xFF])
                opt_cf = bytes([0x60]) + b"\x00"
                payload_marker = bytes([0xFF])
                full_response = header + opt_cf + payload_marker + response
                try:
                    sock.sendto(full_response, addr)
                    print(f"[Multicast] Resposta enviada para {addr}")
                except Exception as e:
                    print(f"[Multicast] Erro ao enviar resposta: {e}")

    sock.close()


async def main():
    site = resource.Site()
    site.add_resource([".well-known", "core"], resource.WKCResource(site.get_resources_as_linkheader))
    site.add_resource(["time"], Time())

    sensor = Sensor()
    site.add_resource(["sensor"], sensor)

    local_ip = get_interface_ip("eth0") or "0.0.0.0"

    await aiocoap.Context.create_server_context(site, bind=(HOST, PORT))
    print(f"CoAP server listening on {HOST}:{PORT}")
    print(f"Local IP: {local_ip}")
    print("Resources: /.well-known/core, /time, /sensor")

    stop_event = threading.Event()
    mcast_thread = threading.Thread(
        target=multicast_discovery_thread,
        args=(local_ip, stop_event),
        daemon=True
    )
    mcast_thread.start()

    sensor.start()

    loop = asyncio.get_running_loop()
    stop_asyncio = asyncio.Event()

    def handle_signal():
        stop_asyncio.set()
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except Exception:
            pass

    await stop_asyncio.wait()
    sensor.stop()
    print("\nServer stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass