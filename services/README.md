# Services

Six short, commented scripts: one server and one client per protocol. Read the top of each
file: it says what the script does and how to run it.

| Protocol | Library  | Server                | Client              |
|----------|----------|-----------------------|---------------------|
| CoAP     | aiocoap  | `coap/server.py`      | `coap/client.py`    |
| mDNS     | zeroconf | `mdns/publisher.py`   | `mdns/browser.py`   |
| SSDP     | ssdpy    | `ssdp/server.py`      | `ssdp/client.py`    |

## How to run

`<ip>` is the IP of **this machine on the LAN** (not `127.0.0.1`, because multicast needs a
real network interface). `<name>` must be different on every server.

```bash
uv sync

# servers
uv run services/coap/server.py                    # optional: [host] [port]
uv run services/mdns/publisher.py <ip> <name>
uv run services/ssdp/server.py    <ip> <name>

# clients
uv run services/coap/client.py <server-ip>        # CoAP does not discover: it needs the address
uv run services/mdns/browser.py <ip> [seconds]    # default 5 s
uv run services/ssdp/client.py <ip>
```

On the Alpine nodes you normally do not call these directly: use the scripts in
`deploy/alpine/` (see [`docs/gns3-setup.md`](../docs/gns3-setup.md)).

## What each one does

- **CoAP server**: a small web-like server over UDP with three resources:
  `/.well-known/core` (list of resources, the CoAP discovery), `/time` (current time) and
  `/sensor` (fake temperature). A client can *observe* `/sensor` and then the server pushes a
  new value every second.
- **CoAP client**: asks for the resource list and the time, then observes `/sensor` for 5
  updates.
- **mDNS publisher**: announces the service `<name>._myservice._tcp.local.` on the LAN. On
  Ctrl+C or SIGTERM it announces that the service is gone ("goodbye").
- **mDNS browser**: listens for announcements and prints `FOUND` / `REMOVED` lines.
- **SSDP server**: answers searches (M-SEARCH) with a `LOCATION`, a URL where a small XML
  description of the device is served.
- **SSDP client**: sends a search, lists the devices that answer and downloads each XML.

## Good to know

- SSDP (ssdpy) answers only when asked: it sends no "I am here" or "I am leaving" messages,
  and it ignores the MX delay. mDNS announces itself and says goodbye.
- The CoAP client does not find servers by itself; it must be given their IP.
- The service port numbers are fixed in the code: CoAP 5683 (UDP), mDNS service 8080
  (advertised only, nothing listens there), SSDP description 8000 (HTTP).
