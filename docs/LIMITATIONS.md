# ReplayGate limitations

- Replays **only** `python -m <module>` commands. This is intentional: it cannot run arbitrary code, network tools, or shell pipelines.
- A `REPLAY_MATCH` means the recorded result reproduced byte-for-byte (same certificate); it does not prove the result is *correct*, only *reproducible*.
- The replayed tool must emit JSON containing at least a `status` (and ideally a `result_body`) for the certificate to be recomputed.
- It does not prove scientific truth or replace experiment, simulation or peer review.
