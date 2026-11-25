# Pitfalls and limitations

Things that can bias the comparison or break a run.

## IGMP snooping

mDNS (224.0.0.251) is always flooded by switches, while SSDP (239.255.255.250) and CoAP
multicast (224.0.1.187) depend on snooping. With snooping and no querier, SSDP "fails"
while mDNS works, and the result reflects the switch, not the protocol. Keep snooping off
(or identical) in all runs. The GNS3 built-in Ethernet switch does not snoop; other switch
images may.

## CoAP IPv4 fallback

Without IPv6 in the kernel, the deployment scripts fall back to aiocoap's
`simplesocketserver` / `simple6` transports, which (as far as I know) do not join CoAP
multicast groups. For a fair discovery comparison, the CoAP nodes need IPv6 and the
`ff02::fd` group. The CoAP client in this repo is unicast only: it does not perform
discovery.

## mDNS name conflicts

Duplicate instance names or host names make zeroconf refuse the registration
(`NonUniqueNameException`). Cloned VMs often share a hostname; the scripts
use the node name given to `run-server.sh` as instance name and host name, so it must be unique per server.

## ssdpy is pull-only and ignores MX

ssdpy answers M-SEARCH but sends no `ssdp:alive` and no `ssdp:byebye`, whereas mDNS
announces and sends goodbyes: arrival and departure results are not symmetric between the
two. ssdpy also answers immediately and ignores MX, so the random response delay that a
spec-compliant SSDP device adds is absent here and SSDP times look better than with a fully
compliant responder.

## Protocol timers

mDNS probing at registration and the mDNS response delay for shared records are protocol
behaviour. Report them separately from network time.

## Emulation effects

- GNS3 links have no delay or loss by default, and QEMU CPU contention adds noise:
  absolute numbers are unrealistic, relative comparisons are fine.
- VM clocks are not synchronised: use capture timestamps from a single host.
- Where the capture point sits relative to the packet filter matters; verify it (see the
  [experiment protocol](experiment-protocol.md#applying-and-calibrating-the-filter)).
- Apply the delay filter to a single link, otherwise latency and jitter accumulate.

## Statistics

With jitter being random, one run per scenario is a very small sample. Repeat runs and
report median and 95th percentile, or state the limitation.

## Known limitations

- The services were validated on a single host without IPv6 (including a simulated second
  server). They have not been run on real Alpine nodes or through GNS3 switches.
- The CoAP IPv6 path (`udp6`, the default when the kernel has IPv6) was not exercised.
- No CoAP multicast discovery; no DTLS or OSCORE; the services are simple mocks.
