"""Minimal CoAP server (aiocoap) — descoberta automática de serviços.

Ambiente: QEMU + GNS3.
Não recebe argumentos de linha de comando. Todos os endereços IP locais
são detectados automaticamente pelo próprio script.

Recursos:
  /.well-known/core  -> listagem de serviços (descoberta CoAP RFC 6690)
  /time              -> hora atual em UTC
  /sensor            -> temperatura simulada; suporta CoAP Observe
"""

import asyncio
import random
import signal
import socket
from datetime import datetime, timezone

import aiocoap
import aiocoap.resource as resource
from aiocoap import Code, Message

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# =============================================================================
HOST = "0.0.0.0"   # Escuta em todas as interfaces IPv4 da VM
PORT = 5683        # Porta padrão CoAP


def get_local_ips():
    """Detecta endereços IP locais (IPv4 e IPv6) da máquina, sem usar internet.

    Combina gethostbyname_ex, getaddrinfo e um bind temporário para descobrir
    os endereços atribuídos às interfaces de rede (útil em QEMU/GNS3).
    """
    ips = set()
    hostname = socket.gethostname()

    # 1) Via gethostbyname_ex (IPv4 associado ao hostname)
    try:
        _, _, addr_list = socket.gethostbyname_ex(hostname)
        for ip in addr_list:
            if ip not in ("127.0.0.1", "0.0.0.0"):
                ips.add(ip)
    except Exception:
        pass

    # 2) Via getaddrinfo (IPv4 e IPv6 associados ao hostname)
    try:
        for res in socket.getaddrinfo(hostname, None, 0, socket.SOCK_DGRAM):
            ip = res[4][0]
            if ip not in ("127.0.0.1", "::1", "0.0.0.0", "::"):
                ips.add(ip)
    except Exception:
        pass

    # 3) Descobre IP da interface de saída default (UDP connect não envia pacote)
    for family in (socket.AF_INET, socket.AF_INET6):
        try:
            s = socket.socket(family, socket.SOCK_DGRAM)
            s.settimeout(0)
            target = ("8.8.8.8", 53) if family == socket.AF_INET else ("2001:4860:4860::8888", 53)
            s.connect(target)
            ip = s.getsockname()[0]
            s.close()
            if ip and ip not in ("0.0.0.0", "::", "127.0.0.1", "::1"):
                ips.add(ip)
        except Exception:
            try:
                s.close()
            except Exception:
                pass

    # 4) Fallback: bind em porta efêmera para obter um IP local válido
    if not ips:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(("0.0.0.0", 0))
            ips.add(s.getsockname()[0])
            s.close()
        except Exception:
            ips.add("0.0.0.0")

    return sorted(ips)


class Time(resource.Resource):
    async def render_get(self, request):
        now = datetime.now(timezone.utc).isoformat()
        return Message(
            code=Code.CONTENT,
            payload=now.encode(),
            content_format=0,  # text/plain
        )

    def get_link_description(self, request=None):
        """Metadados usados na descoberta via /.well-known/core."""
        return {
            "rt": "time.core",
            "if": "core.time",
            "title": "Local time",
        }


class Sensor(resource.ObservableResource):
    def __init__(self):
        super().__init__()
        self.value = 25.0
        self._task = None

    def start(self):
        """Inicia a atualização em background dentro do loop de eventos."""
        if self._task is None:
            self._task = asyncio.get_running_loop().create_task(self.update_forever())

    async def update_forever(self):
        try:
            while True:
                await asyncio.sleep(1)
                self.value = round(random.uniform(20, 30), 2)
                self.updated_state()  # avisa todos os observadores
        except asyncio.CancelledError:
            pass

    async def render_get(self, request):
        return Message(
            code=Code.CONTENT,
            payload=str(self.value).encode(),
            content_format=0,
        )

    def stop(self):
        if self._task is not None:
            self._task.cancel()
            self._task = None

    def get_link_description(self, request=None):
        """Metadados usados na descoberta via /.well-known/core."""
        return {
            "rt": "temperature.sensor",
            "if": "sensor.single",
            "title": "Ambient temperature",
        }


async def main():
    site = resource.Site()

    # Descoberta padrão CoAP (RFC 6690)
    site.add_resource(
        [".well-known", "core"],
        resource.WKCResource(site.get_resources_as_linkheader),
    )

    site.add_resource(["time"], Time())

    sensor = Sensor()
    site.add_resource(["sensor"], sensor)

    # Detecta IPs automaticamente (não vem de argumento nem é hardcoded)
    local_ips = get_local_ips()

    try:
        await aiocoap.Context.create_server_context(site, bind=(HOST, PORT))
    except PermissionError:
        print(f"ERRO: Sem permissão para bind na porta {PORT}. Execute com sudo.")
        raise
    except OSError as e:
        print(f"ERRO ao iniciar CoAP em {HOST}:{PORT}: {e}")
        raise

    print(f"CoAP server listening on {HOST}:{PORT}")
    print(f"Detected local IP(s): {', '.join(local_ips)}")
    print()
    print("Discovery URLs (use any of the IPs above):")
    for ip in local_ips:
        if ":" in ip:
            print(f"  coap://[{ip}]:{PORT}/.well-known/core")
        else:
            print(f"  coap://{ip}:{PORT}/.well-known/core")
    print()
    print("Resources:")
    print("  GET /.well-known/core   -> service discovery")
    print("  GET /time               -> current UTC time")
    print("  GET /sensor             -> simulated temperature (observable)")

    sensor.start()

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def handle_signal():
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_signal)
        except (NotImplementedError, Exception):
            pass

    await stop_event.wait()

    sensor.stop()
    print("\nServer stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
