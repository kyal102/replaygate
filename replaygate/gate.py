"""ReplayGate — re-run evidence packs and detect verification drift.

Given a sealed evidence pack with a ``replay_command``, ReplayGate:
  1. validates the required fields,
  2. validates the replay command is SAFE (Python-module invocation only, no
     shell, no network/file-deleting/remote commands),
  3. executes it with an argument list (``shell=False``) and a short timeout,
  4. recomputes the certificate from the *replayed* status + result body,
  5. compares it to the sealed certificate → ``REPLAY_MATCH`` or ``REPLAY_DRIFT``.

ReplayGate checks whether a recorded result can be reproduced. It does not prove
scientific truth or replace experiment, simulation or peer review.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from typing import Optional

DEFAULT_TIMEOUT_S = 20

# Default allowlist: ONLY local `python -m <module>` commands. With shell=False
# the tokens below cannot chain, but we reject them anyway (defense in depth).
_PY_EXES = ("python", "python3", "py", "python.exe", "python3.exe", "py.exe")
_SHELL_OPS = {"&&", "||", "|", ";", "&", ">", "<", ">>", "<<", "`"}
_BAD_CMDS = {"curl", "wget", "powershell", "pwsh", "bash", "sh", "cmd", "rm",
             "rmdir", "del", "rd", "mkfs", "ssh", "scp", "nc", "sudo", "chmod",
             "chown", "eval", "exec"}
_URLS = ("http://", "https://", "ftp://")

# Certificate fields that do NOT enter the hash (must match EvidencePack).
_CERT_EXCLUDE = {"timestamp", "pack_id", "certificate_hash", "evidence_pack_hash"}
_REQUIRED = ("tool_name", "status", "replay_command", "certificate_hash")


def _canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def certificate_hash(pack: dict) -> str:
    """Recompute a pack's certificate hash (same scheme as EvidencePack)."""
    payload = {k: v for k, v in pack.items() if k not in _CERT_EXCLUDE}
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def is_command_safe(cmd: str) -> tuple[bool, str]:
    """Allowlist: ONLY `python -m <module> [args]`. Tokenised (shell=False), so
    args may contain spaces/quotes; but the executable must be Python, the
    invocation must be a module (`-m`), and no shell operator / destructive
    command / URL token is permitted."""
    c = (cmd or "").strip()
    if not c:
        return False, "empty replay_command"
    try:
        argv = shlex.split(c)
    except ValueError as e:
        return False, f"unparseable command: {e}"
    if not argv:
        return False, "empty command after parsing"
    exe = os.path.basename(argv[0]).lower()
    if exe not in _PY_EXES and os.path.basename(argv[0]) != os.path.basename(sys.executable):
        return False, "only a Python interpreter may be launched"
    if "-c" in argv:
        return False, "arbitrary code (-c) is not allowed; use 'python -m <module>'"
    if "-m" not in argv:
        return False, "command must be 'python -m <module>'"
    mi = argv.index("-m")
    if mi + 1 >= len(argv):
        return False, "no module name after -m"
    module = argv[mi + 1]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", module):
        return False, f"unsafe module name: {module!r}"
    for tok in argv:
        if tok in _SHELL_OPS:
            return False, f"shell operator not allowed: {tok!r}"
        if os.path.basename(tok).lower() in _BAD_CMDS:
            return False, f"unsafe command token: {tok!r}"
        if any(u in tok.lower() for u in _URLS):
            return False, "network URL not allowed in replay_command"
    return True, "ok"


def _run(cmd: str, timeout_s: int) -> tuple[Optional[dict], str]:
    argv = shlex.split(cmd)
    if argv and argv[0].lower() in ("python", "python3", "py"):
        argv[0] = sys.executable
    try:
        proc = subprocess.run(argv, shell=False, capture_output=True, text=True,
                              timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return None, "REPLAY_TIMEOUT"
    except Exception as e:                       # pragma: no cover
        return None, f"REPLAY_COMMAND_FAILED: {e}"
    if proc.returncode != 0:
        return None, f"REPLAY_COMMAND_FAILED: exit {proc.returncode}"
    out = proc.stdout or ""
    try:
        return json.loads(out[out.find("{"):out.rfind("}") + 1]), ""
    except Exception:
        return None, "UNVERIFIABLE_ARTIFACT: replayed output is not JSON"


def replay(pack: dict, timeout_s: int = DEFAULT_TIMEOUT_S) -> dict:
    missing = [f for f in _REQUIRED if not pack.get(f)]
    if missing:
        return _result("MISSING_FIELDS", pack, note=f"pack missing: {', '.join(missing)}")
    ok, why = is_command_safe(pack["replay_command"])
    if not ok:
        return _result("UNSAFE_REPLAY_COMMAND", pack, note=why)
    replayed, err = _run(pack["replay_command"], timeout_s)
    if replayed is None:
        return _result(err.split(":")[0], pack, note=err)
    # recompute the certificate from the REPLAYED status + result body
    candidate = dict(pack)
    candidate["status"] = replayed.get("status", pack.get("status"))
    candidate["result_body"] = replayed.get("result_body", replayed)
    recomputed = certificate_hash(candidate)
    match = (recomputed == pack["certificate_hash"])
    return _result("REPLAY_MATCH" if match else "REPLAY_DRIFT", pack,
                   replayed_status=candidate["status"],
                   recomputed_certificate_hash=recomputed,
                   sealed_certificate_hash=pack["certificate_hash"])


def diff_packs(a: dict, b: dict) -> dict:
    match = a.get("certificate_hash") == b.get("certificate_hash")
    return {"tool": "replaygate", "status": "REPLAY_MATCH" if match else "REPLAY_DRIFT",
            "a_certificate_hash": a.get("certificate_hash"),
            "b_certificate_hash": b.get("certificate_hash"),
            "public_wording": _WORDING}


_WORDING = ("ReplayGate checks whether a recorded result can be reproduced. It "
            "does not prove scientific truth or replace experiment, simulation "
            "or peer review.")


def _result(status: str, pack: dict, **extra) -> dict:
    return {"tool": "replaygate", "status": status, "pack_id": pack.get("pack_id"),
            "public_wording": _WORDING, **extra}
