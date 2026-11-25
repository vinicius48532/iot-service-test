# Experiments

```
experiments/
├── captures/        # packet captures (.pcapng), committed when small
│   └── large/       # git-ignored: big captures, attach them to a release instead
└── results/
    └── run-log.csv  # one line per run (see docs/experiment-protocol.md)
```

## Capture naming

`<protocol>_<scenario>_<nn>.pcapng`

- `protocol`: `ssdp`, `mdns` or `coap`
- `scenario`: `none`, `stable`, `moderate`, `unstable` or `very_unstable`
- `nn`: run number, zero-padded

Example: `mdns_unstable_03.pcapng`.

See [`docs/experiment-protocol.md`](../docs/experiment-protocol.md) for the run procedure and
[`docs/metrics.md`](../docs/metrics.md) for how to extract the metrics.
