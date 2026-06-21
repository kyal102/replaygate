"""Tiny module so ReplayGate demos/tests use a real `python -m` replay command.

    python -m replaygate._echo DIMENSIONALLY_INVALID
    -> {"status": "DIMENSIONALLY_INVALID", "result_body": {"verdict": "DIMENSIONALLY_INVALID"}}
"""
import json
import sys

status = sys.argv[1] if len(sys.argv) > 1 else "UNKNOWN"
print(json.dumps({"status": status, "result_body": {"verdict": status}}))
