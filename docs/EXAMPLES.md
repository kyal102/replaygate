# ReplayGate examples

```bash
python -m replaygate --demo
# reproducible pack -> REPLAY_MATCH
# drifted pack      -> REPLAY_DRIFT
# unsafe command    -> UNSAFE_REPLAY_COMMAND

python -m replaygate pack.json            # replay a real pack
python -m replaygate pack.json --json     # full JSON verdict
python -m replaygate a.json b.json --diff # compare two packs by certificate hash
```

Rejected replay commands (examples): `curl http://...`, `rm -rf /`, `python -m x && rm y`,
`python -m x | tee z`, `powershell -c ...`, `python -c "..."` (arbitrary code).
