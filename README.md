# IoT Service Discovery

Educational comparison of three service-discovery protocols under emulated network
conditions:

| Protocol | Library  | Role in this repo                         |
|----------|----------|-------------------------------------------|
| SSDP     | ssdpy    | UPnP-style discovery (M-SEARCH + LOCATION)|
| mDNS / DNS-SD | zeroconf | Zero-configuration discovery         |
| CoAP     | aiocoap  | Constrained REST with resource discovery  |

The services run on Alpine Linux nodes in a GNS3 lab (`consumer - sw1 - sw2 - server1/server2`).
Network latency and jitter are emulated with GNS3 packet filters, and the results are
extracted from packet captures.

## Repository layout

```
.
├── services/        # standalone scripts: one server + one client per protocol
│   ├── coap/        #   server.py, client.py
│   ├── mdns/        #   publisher.py, browser.py
│   └── ssdp/        #   server.py, client.py
├── deploy/alpine/   # setup / run / stop / consumer scripts for the Alpine nodes
├── docs/            # lab setup, experiment protocol, metrics, pitfalls
├── experiments/     # captures/ (pcapng) and results/ (run log, tables)
└── src/             # (uv project skeleton, not used by the services)
```

## Quick start (local)

```bash
uv sync

# terminal 1: a server (use your computer's LAN IP, not 127.0.0.1)
uv run services/ssdp/server.py 192.168.1.20 server1
# terminal 2: a client
uv run services/ssdp/client.py 192.168.1.20
```

The same pattern works for `services/mdns/` and `services/coap/`. Each script is short and
commented; how to run them is described in [`services/README.md`](services/README.md).

## Documentation

| Document | Content |
|----------|---------|
| [`docs/gns3-setup.md`](docs/gns3-setup.md) | Topology, addressing, Alpine setup, running the servers and the consumer |
| [`docs/experiment-protocol.md`](docs/experiment-protocol.md) | Network scenarios, GNS3 packet filters, calibration, step-by-step run procedure |
| [`docs/metrics.md`](docs/metrics.md) | The six evaluation metrics: definition and how to extract them |
| [`docs/pitfalls.md`](docs/pitfalls.md) | Sources of bias, limitations, troubleshooting |

## Status

The services were validated on a single host (including a simulated second server).
They have not yet been run on real Alpine nodes or through GNS3 switches. See
[`docs/pitfalls.md`](docs/pitfalls.md#known-limitations).
