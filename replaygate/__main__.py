"""CLI:
  python -m replaygate --demo
  python -m replaygate pack.json
  python -m replaygate pack.json --json
  python -m replaygate pack_a.json pack_b.json --diff
"""
import argparse
import json
import sys

from .gate import replay, diff_packs, certificate_hash


def _seal(status, result_body, replay_command):
    pack = {"tool_name": "demo", "tool_version": "0.1.0",
            "normalized_input": "demo claim", "status": status,
            "result_body": result_body, "replay_command": replay_command,
            "schema_version": "evidencepack/v0.1"}
    pack["certificate_hash"] = certificate_hash(pack)
    pack["pack_id"] = "ev_" + pack["certificate_hash"][:16]
    return pack


def _demo():
    emit = "python -m replaygate._echo %s"
    good = _seal("DIMENSIONALLY_INVALID", {"verdict": "DIMENSIONALLY_INVALID"},
                 emit % "DIMENSIONALLY_INVALID")
    drift = _seal("DIMENSIONALLY_INVALID", {"verdict": "DIMENSIONALLY_INVALID"},
                  emit % "DIMENSIONALLY_VALID")
    unsafe = _seal("X", {"v": 1}, "curl http://evil.example.com")
    print("# reproducible pack ->", replay(good)["status"])
    print(json.dumps(replay(good), indent=2))
    print("\n# drifted pack ->", replay(drift)["status"])
    print("\n# unsafe replay_command ->", replay(unsafe)["status"])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="replaygate",
                                 description="Re-run evidence packs and detect drift.")
    ap.add_argument("pack", nargs="?")
    ap.add_argument("pack_b", nargs="?")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--diff", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.demo or not args.pack:
        return _demo()
    if args.diff and args.pack_b:
        res = diff_packs(json.load(open(args.pack, encoding="utf-8")),
                         json.load(open(args.pack_b, encoding="utf-8")))
    else:
        res = replay(json.load(open(args.pack, encoding="utf-8")))
    print(json.dumps(res, indent=2) if args.json else f"{res['status']}  ({res.get('pack_id','')})")
    return 0 if res["status"] in ("REPLAY_MATCH",) else 1


if __name__ == "__main__":
    sys.exit(main())
