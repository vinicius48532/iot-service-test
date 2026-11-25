# Evaluation metrics

Six metrics, all extracted from packet captures taken on the consumer side (timestamps
come from the GNS3 host clock; never compute latencies from timestamps taken inside
different VMs, whose clocks are not synchronised).

**Reference time `t0`**: timestamp of the consumer's first discovery packet.
SSDP: the M-SEARCH. mDNS: the first PTR query for the service type. CoAP: the first request
(`GET /.well-known/core`).

| # | Metric | Why it matters |
|---|--------|----------------|
| M1 | Discovery time | Main metric: how much each scenario delays discovery |
| M2 | Time to usable information | Differentiates protocols by number of round trips |
| M3 | Success rate | Robustness when the network degrades |
| M4 | Overhead (packets and bytes) | Network cost of each protocol |
| M5 | Application-level latency and jitter | How much of the configured jitter reaches the application |
| M6 | Arrival and departure detection | Push versus pull models |

## M1 - Discovery time

Time from `t0` to the response of the **last** server to answer (both servers discovered).
Also report the time to the **first** response.

- SSDP: M-SEARCH to the responses of both servers (`udp.port == 1900`).
- mDNS: first query to the answers of both instances (`mdns`).
- CoAP: the `/.well-known/core` request/response with each server (the client contacts the
  servers one after the other; use only that exchange, not the rest of the client sequence).

## M2 - Time to usable information

Time from `t0` until the consumer holds what it needs to reach the service (host, port, and
how to query it).

- SSDP: M-SEARCH, then the HTTP GET of the `LOCATION` XML (a TCP handshake plus the request;
  filter `http.request or http.response`). Expected: about 3 round trips.
- mDNS: PTR query until the SRV, TXT and address records have arrived (often in the same
  response as additional records). Expected: about 1 round trip.
- CoAP: the `/.well-known/core` response lists the resources, so M2 is close to M1.
  Expected: about 1 round trip.

These expectations are hypotheses to verify, not results.

## M3 - Success rate

Servers found (out of 2) within the client's window (SSDP client: 3 s idle timeout, mDNS
browser: 5 s total). Across repeated runs, report the percentage of runs in which both
servers were found. Record the window next to the result.

## M4 - Overhead

Packets and bytes (`frame.len`) exchanged from `t0` to the end of M2, split by direction and
by multicast versus unicast. Include retransmissions and duplicate packets. Filter by
protocol port and addresses to exclude unrelated traffic (ARP, background).

Also report message sizes (mean and maximum): DNS messages are binary, SSDP uses text
headers similar to HTTP, CoAP is binary with a 4-byte header.

## M5 - Application-level latency and jitter

- **RTT per exchange**: response time minus request time, on the consumer capture. CoAP:
  pair requests and responses by message ID or token. SSDP and mDNS: query to each answer.
  Report mean, standard deviation and 95th percentile; compare with the measured RTT from the
  ping calibration.
- **Notification jitter (CoAP Observe)**: inter-arrival times of the `/sensor` notifications at
  the consumer. The server pushes a new value every second, so the expected period is 1 s. Jitter =
  standard deviation of the inter-arrival times. Compare it with the `stable` scenario to
  isolate the effect of the network from the server's own timer and Python scheduling.
- **Jitter propagation**: observed jitter divided by configured jitter (undefined for 0 ms;
  report the absolute value instead).

SSDP and mDNS exchange only a few packets per discovery, so their jitter can only be
estimated roughly in a single run; repeated runs are needed.

## M6 - Arrival and departure detection

Qualitative plus one timing per protocol:

| Event | mDNS | SSDP (ssdpy) | CoAP |
|-------|------|--------------|------|
| Server arrives while the consumer is listening | Announcements (push); time until `browser.py` prints `FOUND` | No `ssdp:alive`: only seen on the next M-SEARCH (pull) | Not applicable (unicast) |
| Server leaves | Goodbye packet (TTL 0); time until `REMOVED` is printed | No `ssdp:byebye`: stale until `max-age` (1800 s) | Not applicable |

mDNS goodbyes can be found with the filter `mdns && dns.resp.ttl == 0`.

## Extraction

```sh
# packet list with times, endpoints and sizes
tshark -r ssdp_stable_01.pcapng -Y "udp.port == 1900" \
  -T fields -e frame.time_relative -e ip.src -e ip.dst -e frame.len

tshark -r mdns_stable_01.pcapng -Y mdns \
  -T fields -e frame.time_relative -e ip.src -e dns.flags.response -e dns.qry.name -e frame.len

# totals
tshark -r file.pcapng -q -z conv,udp     # UDP conversations: packets and bytes
tshark -r file.pcapng -q -z io,phs       # protocol hierarchy

# CoAP field names available in your Wireshark version
tshark -G fields | grep -i coap
```

In the Wireshark GUI: *Statistics > Conversations*, *Protocol Hierarchy* and *I/O Graphs*.
