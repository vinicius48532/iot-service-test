# Experiment protocol

## Network scenarios

Latency and jitter are applied with the GNS3 link **Packet filters** (Delay).

| ID              | Description         | Latency | Jitter |
|-----------------|---------------------|--------:|-------:|
| `none`          | control, no filter  | -       | -      |
| `stable`        | stable network      | 5 ms    | 0 ms   |
| `moderate`      | moderate network    | 30 ms   | 10 ms  |
| `unstable`      | unstable network    | 50 ms   | 20 ms  |
| `very_unstable` | very unstable       | 100 ms  | 50 ms  |

The scenarios contain no packet loss. Loss is what exercises each protocol's recovery
mechanisms (CoAP retransmission, repeated mDNS queries, the single M-SEARCH of ssdpy), so
consider adding optional scenarios such as `loss5` and `loss10` (GNS3 also has a packet loss
filter).

Use the scenario ID in capture names and in the run log.

## Applying and calibrating the filter

1. Apply the filter on **one link only**, for example `consumer - sw1`, so that both servers
   see identical conditions. The path has three links; filtering all of them accumulates the
   latency and the jitter.
2. Check what was really applied. From the consumer, ping a server 100 times:

   ```sh
   ping -c 100 192.168.10.11 | tee ping.log
   awk -F'time=' '/time=/{split($2,a," "); n++; s+=a[1]; ss+=a[1]*a[1]}
        END{m=s/n; printf "n=%d mean=%.2f ms stdev=%.2f ms\n", n, m, sqrt(ss/n-m*m)}' ping.log
   ```

   The mean RTT shows whether the configured latency applies per direction or per link
   (RTT = 2x or 1x the latency). Record the measured values; report them next to the
   configured ones.
3. Confirm that the capture point sees the effect of the filter. If you capture on the same
   link that carries the filter and the delay is not visible in the timestamps, capture on a
   neighbouring link (for example filter on `consumer - sw1`, capture on `sw1 - sw2`).
4. Jitter may reorder packets. Count reordered packets as a result, not as an error.

## One run (one protocol, one scenario)

Run the protocols in isolation (`PROTO=ssdp`, `PROTO=mdns`, `PROTO=coap`), so that one
protocol's traffic and CPU use do not pollute another one's capture.

1. Stop everything on the servers: `sh deploy/alpine/stop-server.sh`.
2. Set the scenario filter and calibrate it (above).
3. **Warm up ARP**, outside the capture: from the consumer, `ping -c 2` both servers. Without
   it, the first unicast packet (SSDP response, CoAP GET) includes an ARP resolution and
   distorts the measurement.
4. Start a capture on the chosen link (GNS3: right-click the link, *Start capture*).
5. On the servers: `PROTO=<proto> sh deploy/alpine/run-server.sh <ip> <name>`. Wait a few
   seconds (mDNS probes and announces when registering). To measure registration, start the
   capture *before* this step.
6. On the consumer: `PROTO=<proto> sh deploy/alpine/consumer.sh <consumer-ip> [server-ips]`.
7. To measure service departure: `sh deploy/alpine/stop-server.sh` and watch for the mDNS
   goodbye (ssdpy has no `ssdp:byebye`).
8. Stop the capture. Save it as `experiments/captures/<protocol>_<scenario>_<nn>.pcapng`
   (for example `ssdp_unstable_01.pcapng`). Large captures go to
   `experiments/captures/large/`, which is git-ignored (attach them to a release).
9. Add a line to `experiments/results/run-log.csv`.

## Repetitions

Jitter is random, so a single run per scenario is a very small sample. If possible, repeat
every protocol x scenario combination about 10 times, randomise the order of scenarios and
protocols to avoid drift, and report the median and the 95th percentile. With a single run,
state that explicitly and avoid statistical claims.

## What to record for each run

`experiments/results/run-log.csv` columns:

| Column | Meaning |
|--------|---------|
| `run_id`, `date`, `run_number` | Identification |
| `protocol`, `scenario` | `ssdp` / `mdns` / `coap`; scenario ID |
| `configured_latency_ms`, `configured_jitter_ms` | What the filter was set to |
| `measured_rtt_mean_ms`, `measured_rtt_stdev_ms` | From the ping calibration |
| `igmp_snooping`, `ipv6` | Conditions that bias the comparison |
| `lib_versions` | e.g. `ssdpy 0.4.1, zeroconf 0.154.0, aiocoap 0.4.17` |
| `capture_file`, `notes` | Capture name and free text |
