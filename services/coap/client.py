"""Minimal CoAP client (aiocoap) — descoberta automática de serviços.

Não recebe argumentos de linha de comando. Toda a configuração está
dentro do script. Descobre os serviços consultando /.well-known/core
no alvo configurado.
"""

import asyncio
import re

from aiocoap import Code, Context, Message

# =============================================================================
# Configurações fixas (sem argumentos de linha de comando)
# Altere TARGET_HOST para o IP da VM do servidor no GNS3.
# =============================================================================
TARGET_HOST = "127.0.0.1"   # Exemplo: "10.0.0.15"
TARGET_PORT = 5683


def parse_link_header(header_text: str):
    """Parse simples do formato CoAP Link Format (RFC 6690).

    Retorna lista de dicionários com os atributos de cada recurso.
    Exemplo de entrada:
        </.well-known/core>,
        </time>;rt="time.core";if="core.time";title="Local time",
        </sensor>;rt="temperature.sensor";if="sensor.single";title="Ambient temperature"
    """
    resources = []
    # Separa por vírgula que não está dentro de aspas
    parts = re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', header_text)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = re.match(r'<([^>]+)>(.*)', part, re.DOTALL)
        if not match:
            continue
        uri = match.group(1)
        attrs = match.group(2).strip()
        entry = {"uri": uri}

        # Atributos chave="valor" (rt, if, title, etc.)
        for attr in re.finditer(r'(\w+)="([^"]*)"', attrs):
            entry[attr.group(1)] = attr.group(2)

        # Atributos booleanos (ex: observe)
        for attr in re.finditer(r'(\w+)(?=\s*$|\s*;|\s*,)', attrs):
            key = attr.group(1)
            if key not in entry:
                entry[key] = True

        resources.append(entry)
    return resources


async def discover_services(ctx):
    """Consulta /.well-known/core e imprime os serviços descobertos."""
    uri = f"coap://{TARGET_HOST}:{TARGET_PORT}/.well-known/core"
    request = Message(code=Code.GET, uri=uri)
    try:
        response = await ctx.request(request).response
    except Exception as e:
        print(f"Erro ao consultar descoberta em {uri}: {e}")
        return []

    payload = response.payload.decode(errors="replace")
    print(f"GET /.well-known/core -> {response.code}")
    print(f"Payload: {payload}")
    print()

    resources = parse_link_header(payload)
    print("Serviços descobertos automaticamente:")
    for r in resources:
        print(f"  URI: {r.get('uri')}")
        print(f"    rt (resource type): {r.get('rt', 'N/A')}")
        print(f"    if (interface): {r.get('if', 'N/A')}")
        print(f"    title: {r.get('title', 'N/A')}")
        print()
    return resources


async def fetch_resource(ctx, path):
    """Faz GET simples em um recurso."""
    uri = f"coap://{TARGET_HOST}:{TARGET_PORT}{path}"
    request = Message(code=Code.GET, uri=uri)
    try:
        response = await ctx.request(request).response
        print(f"GET {path} -> {response.code}: {response.payload.decode()}")
    except Exception as e:
        print(f"Erro ao acessar {path}: {e}")


async def observe_sensor(ctx):
    """Faz observe em /sensor por 5 atualizações."""
    uri = f"coap://{TARGET_HOST}:{TARGET_PORT}/sensor"
    request = Message(code=Code.GET, uri=uri, observe=0)
    try:
        pending = ctx.request(request)
        first = await pending.response
        print(f"OBSERVE /sensor -> {first.code}: {first.payload.decode()}")
        count = 0
        async for update in pending.observation:
            print(f"OBSERVE /sensor -> {update.code}: {update.payload.decode()}")
            count += 1
            if count >= 5:
                pending.observation.cancel()
                break
    except Exception as e:
        print(f"Erro no observe de /sensor: {e}")


async def main():
    ctx = await Context.create_client_context()

    try:
        # 1) Descoberta automática de serviços
        await discover_services(ctx)

        # 2) Acessa recursos com base na descoberta (exemplo: /time)
        await fetch_resource(ctx, "/time")

        # 3) Observe em /sensor
        await observe_sensor(ctx)

    finally:
        await ctx.shutdown()


asyncio.run(main())
