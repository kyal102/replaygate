import unittest
from replaygate import replay, is_command_safe, certificate_hash

EMIT = "python -m replaygate._echo %s"


def _seal(status, rb, cmd):
    p = {"tool_name": "t", "tool_version": "1", "normalized_input": "x",
         "status": status, "result_body": rb, "replay_command": cmd}
    p["certificate_hash"] = certificate_hash(p)
    p["pack_id"] = "ev_" + p["certificate_hash"][:16]
    return p


class TestReplayGate(unittest.TestCase):
    def test_reproducible_pack_matches(self):
        p = _seal("INVALID", {"verdict": "INVALID"}, EMIT % "INVALID")
        self.assertEqual(replay(p)["status"], "REPLAY_MATCH")

    def test_drifted_pack_detected(self):
        p = _seal("INVALID", {"verdict": "INVALID"}, EMIT % "VALID")
        self.assertEqual(replay(p)["status"], "REPLAY_DRIFT")

    def test_unsafe_commands_rejected(self):
        for bad in ["curl http://evil.com", "rm -rf /", "python -m x && rm y",
                    "powershell -c x", "python -m x | tee z", "wget http://x",
                    "python -c \"print(1)\"", "python -m x; rm y"]:
            self.assertFalse(is_command_safe(bad)[0], bad)

    def test_safe_module_command_allowed(self):
        self.assertTrue(is_command_safe('python -m unitgate --json "E = m * a"')[0])
        self.assertTrue(is_command_safe("python -m replaygate._echo INVALID")[0])

    def test_unsafe_pack_refused(self):
        p = _seal("X", {"v": 1}, "curl http://evil.example.com")
        self.assertEqual(replay(p)["status"], "UNSAFE_REPLAY_COMMAND")

    def test_missing_fields(self):
        self.assertEqual(replay({"tool_name": "t"})["status"], "MISSING_FIELDS")


if __name__ == "__main__":
    unittest.main()
