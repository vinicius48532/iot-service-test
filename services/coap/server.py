"""Minimal CoAP server (aiocoap).

Usage:  python server.py [host] [port]      (defaults: "::" and 5683)

Resources:
  /.well-known/core  -> list of the server's resources (discovery, automatic)
  /time              -> current time
  /sensor            -> fake temperature; a client can "observe" it, and then
                        the server pushes a new value every second
"""

import asyncio
import random
import sys
from datetime import datetime, timezone

import aiocoap
import aiocoap.resource as resource
from aiocoap import Code, Message


class Time(resource.Resource):
    async def render_get(self, request):  # called on GET /time
        now = datetime.now(timezone.utc).isoformat()
        return Message(code=Code.CONTENT, payload=now.encode())


class Sensor(resource.ObservableResource):
    def __init__(self):
        super().__init__()
        self.value = 25.0
        # background task: change the value every second
        self.task = asyncio.get_running_loop().create_task(self.update_forever())

    async def update_forever(self):
        while True:
            await asyncio.sleep(1)
            self.value = round(random.uniform(20, 30), 2)
            self.updated_state()  # tells every observer "I changed"

    async def render_get(self, request):  # called on GET /sensor
        return Message(code=Code.CONTENT, payload=str(self.value).encode())


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "::"  # "::" = IPv4 and IPv6
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5683

    site = resource.Site()  # the "tree" of resources
    site.add_resource(
        [".well-known", "core"],
        resource.WKCResource(site.get_resources_as_linkheader),
    )
    site.add_resource(["time"], Time())
    site.add_resource(["sensor"], Sensor())

    await aiocoap.Context.create_server_context(site, bind=(host, port))
    print(f"CoAP server listening on {host}:{port}")
    await asyncio.get_running_loop().create_future()  # run forever


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
