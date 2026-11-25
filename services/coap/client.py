"""Minimal CoAP client (aiocoap).

Usage:  python client.py <server>      e.g.  python client.py 192.168.10.11
"""

import asyncio
import sys

from aiocoap import Code, Context, Message

server = sys.argv[1] if len(sys.argv) > 1 else "localhost"


async def main():
    ctx = await Context.create_client_context()

    # 1) plain requests: ask for the resource list, then for the time
    for path in ["/.well-known/core", "/time"]:
        request = Message(code=Code.GET, uri=f"coap://{server}{path}")
        response = await ctx.request(request).response
        print(f"GET {path} -> {response.code}: {response.payload.decode()}")

    # 2) observe: ask the server to push every change of /sensor (5 pushes)
    request = Message(code=Code.GET, uri=f"coap://{server}/sensor", observe=0)
    pending = ctx.request(request)
    first = await pending.response
    print(f"OBSERVE /sensor: {first.payload.decode()}")
    count = 0
    async for update in pending.observation:
        print(f"OBSERVE /sensor: {update.payload.decode()}")
        count += 1
        if count == 5:
            pending.observation.cancel()
            break

    await ctx.shutdown()


asyncio.run(main())
