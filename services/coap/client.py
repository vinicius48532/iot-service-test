"""Minimal CoAP client (aiocoap) — descoberta automática por multicast.

Ambiente: QEMU + GNS3. Sem dependência de internet.
Não recebe argumentos de linha de comando.

Estratégia de descoberta:
  1. Multicast CoAP para 224.0.1.187:5683 (All CoAP Nodes, RFC 7390)
     Somente multicast, sem varredura unicast.
"""

import asyncio
import fcntl
import socket
import struct

from aiocoap import Code, Context, Message

COAP_PORT = 5683
MCAST_GROUP = "224.0.1.187"   # All CoAP Nodes (RFC 7390)


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


def parse_link_header(text: str):
    resources = []
    parts = text.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Separa URI dos atributos
        if ";" in part:
            uri_part, attrs_part = part.split(";", 1)
        else:
            uri_part = part
            attrs_part = ""
        uri = uri_part.strip().strip("<").strip(">")
        entry = {"uri": uri}
        for attr in attrs_part.split(";"):
            attr = attr.strip()
            if not attr:
                continue
            if "=" in attr:
                key, val = attr.split("=", 1)
                entry[key.strip()] = val.strip().strip('"')
            else:
                entry[attr] = True
        resources.append(entry)
    return resources


def build_get_wellknown_coap():
    msg_id = 0x1234
    header = bytes([0x40, 0x01, (msg_id >> 8) & 0xFF, msg_id & 0xFF])
    opt1 = bytes([0xBA]) + b"well-known"
    opt2 = bytes([0x04]) + b"core"
    return header + opt1 + opt2


async def discover_multicast(local_ip):
    found = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(local_ip))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.bind(("0.0.0.0", COAP_PORT))
    sock.settimeout(2.0)

    payload = build_get_wellknown_coap()
    print(f"[Multicast] Enviando GET /.well-known/core para {MCAST_GROUP}:{COAP_PORT}")
    sock.sendto(payload, (MCAST_GROUP, COAP_PORT))

    loop = asyncio.get_running_loop()
    deadline = loop.time() + 5.0

    while loop.time() < deadline:
        remaining = deadline - loop.time()
        if remaining <= 0:
            break
        try:
            sock.settimeout(remaining)
            data, addr = sock.recvfrom(2048)
        except socket.timeout:
            break
        except Exception:
            break

        ip_resp = addr[0]
        if ip_resp in [f["ip"] for f in found]:
            continue

        payload_text = ""
        if 0xFF in data:
            idx = data.index(0xFF)
            payload_text = data[idx + 1:].decode(errors="replace")

        print(f"  [+] Servidor descoberto via multicast em {ip_resp}")
        if payload_text:
            print(f"      Payload: {payload_text[:120]}")
            resources = parse_link_header(payload_text)
            for r in resources:
                print(f"          {r.get('uri')} rt={r.get('rt','?')} if={r.get('if','?')}")
        else:
            print(f"      (sem payload link-format)")

        found.append({"ip": ip_resp, "resources": parse_link_header(payload_text)})

    sock.close()
    return found


async def access_resource(ctx, ip, path):
    uri = f"coap://{ip}:{COAP_PORT}{path}"
    req = Message(code=Code.GET, uri=uri)
    try:
        resp = await asyncio.wait_for(ctx.request(req).response, timeout=3)
        print(f"GET {path} de {ip} -> {resp.code}: {resp.payload.decode()}")
    except Exception as e:
        print(f"Erro ao acessar {path} em {ip}: {e}")


async def observe_sensor(ctx, ip):
    uri = f"coap://{ip}:{COAP_PORT}/sensor"
    req = Message(code=Code.GET, uri=uri, observe=0)
    try:
        pending = ctx.request(req)
        first = await pending.response
        print(f"OBSERVE /sensor de {ip} -> {first.code}: {first.payload.decode()}")
        count = 0
        async for update in pending.observation:
            print(f"OBSERVE /sensor de {ip} -> {update.code}: {update.payload.decode()}")
            count += 1
            if count >= 4:
                pending.observation.cancel()
                break
    except Exception as e:
        print(f"Erro no observe de /sensor em {ip}: {e}")


async def main():
    ctx = await Context.create_client_context()

    local_ip = get_interface_ip("eth0") or "127.0.0.1"
    print(f"IP local: {local_ip}")
    print()

    print("=== DESCOBERTA SOMENTE VIA MULTICAST CoAP ===")
    found = await discover_multicast(local_ip)

    if not found:
        print("Nenhum servidor CoAP encontrado via multicast.")
        await ctx.shutdown()
        return

    print(f"\n{len(found)} servidor(es) descoberto(s):")
    for f in found:
        print(f"  - {f['ip']}")

    target = found[0]["ip"]
    print(f"\nUsando primeiro servidor descoberto: {target}\n")

    # Acesso aos recursos via unicast (descoberta já foi feita por multicast)
    await access_resource(ctx, target, "/.well-known/core")
    await access_resource(ctx, target, "/time")
    await observe_sensor(ctx, target)

    await ctx.shutdown()


asyncio.run(main())