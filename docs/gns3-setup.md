# GNS3 + Alpine setup

## Topology

Single subnet and VLAN (mDNS and SSDP multicast do not cross routers):

```
consumer ── sw1 ── sw2 ──┬── server1
                         └── server2
```

| Node     | IP               | Role                                 |
|----------|------------------|--------------------------------------|
| consumer | 192.168.10.10/24 | runs the clients                     |
| server1  | 192.168.10.11/24 | CoAP + mDNS + SSDP                   |
| server2  | 192.168.10.12/24 | CoAP + mDNS + SSDP                   |

## 1. Network setup on each Alpine node

`/etc/network/interfaces` (check the interface name with `ip link`, usually `eth0`):

```
auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 192.168.10.11/24
```

```sh
echo server1 > /etc/hostname && hostname server1   # must be unique on every node!
rc-service networking restart
```

## 2. Install (once per node, needs internet)

Temporarily attach a **NAT** node to a second interface (DHCP), and enable the
`community` repository if `apk` cannot find packages.

```sh
sh deploy/alpine/setup.sh   # apk add python3 py3-pip + .venv with aiocoap, zeroconf, ssdpy
```

The nodes do not need `uv`: the setup script installs the three libraries with `pip`.
Check `python3 --version` on the node; the scripts use no syntax newer than Python 3.8,
and pip will complain if a library needs a newer interpreter.

If Alpine runs in **diskless / RAM** mode (booted from the ISO), everything is lost on
power-off: install to disk (`setup-alpine`, `sys` mode) or use `lbu commit`.
Tip: install on one node, then clone its QEMU disk for the others.

## 3. Copy the repository to the nodes

Any way works: a NAT node + `wget` from `python3 -m http.server` on your computer, `scp`,
or pasting through the console. Copy at least `services/` and `deploy/` and keep the layout
(for example in `/opt/iot-service-discovery`).

## 4. Start the servers

```sh
# server1
sh deploy/alpine/run-server.sh 192.168.10.11 server1
# server2
sh deploy/alpine/run-server.sh 192.168.10.12 server2
```

The name is used for the mDNS instance (`server1._myservice._tcp.local.`), the mDNS host
name (`server1.local.`) and a stable SSDP UUID (same name, same USN). Logs go to `logs/`.
Stop with `sh deploy/alpine/stop-server.sh`.

## 5. Discover from the consumer

```sh
PROTO=ssdp sh deploy/alpine/consumer.sh 192.168.10.10
PROTO=mdns sh deploy/alpine/consumer.sh 192.168.10.10
PROTO=coap sh deploy/alpine/consumer.sh 192.168.10.10 192.168.10.11 192.168.10.12
```

The **first argument is the consumer's own LAN IP** (so multicast leaves through the right
interface). The server IPs are only needed by CoAP, which here is unicast: the client must
already know the server address. SSDP and mDNS discover the servers by themselves.
Expected: **2** devices from SSDP and **2** instances from mDNS.

`PROTO` (`all` by default, `coap`, `mdns` or `ssdp`) works the same way in `run-server.sh`
and `consumer.sh`.

## Troubleshooting

- **SSDP finds nothing but mDNS works:** IGMP snooping without a querier (see
  [pitfalls](pitfalls.md#igmp-snooping)).
- **Nothing across sw1 and sw2:** check VLAN / trunk between the switches.
- **mDNS `NonUniqueNameException` on start:** two servers started with the same name (the second argument of `run-server.sh`).
- **CoAP `Address family not supported`:** kernel without IPv6; the scripts already use the
  IPv4 fallback (which has consequences, see [pitfalls](pitfalls.md#coap-ipv4-fallback)).
- **Wrong interface / extra NICs (e.g. NAT):** always pass the LAN interface IP to the
  scripts.
- **Containers on a bridge network** usually do not forward multicast; use host networking.
