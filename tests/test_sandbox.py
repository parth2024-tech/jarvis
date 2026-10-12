import unittest
import sys
import os

sys.path.append("/home/thor/Desktop/JARVIS/core")
from sandbox import secure_execute, ALLOWED_BINARIES, SANDBOX_LOG

class TestSandbox(unittest.TestCase):
    def test_01_allowed_binaries_execution(self):
        res = secure_execute("echo 'Hello JARVIS Sandbox'")
        self.assertTrue(res["success"])
        self.assertEqual(res["exit_code"], 0)
        self.assertIn("Hello JARVIS Sandbox", res["output"])

    def test_02_unauthorized_binaries_blocked(self):
        unauthorized_cmds = [
            "curl https://example.com",
            "python3 -c 'print(1)'",
            "bash -c 'echo pwned'",
            "cat /etc/passwd",
            "nc -l 1234"
        ]
        for cmd in unauthorized_cmds:
            res = secure_execute(cmd)
            self.assertFalse(res["success"])
            self.assertIn("SECURITY EXCEPTION", res["output"])
            self.assertIn("not permitted under the strict execution policy allowlist", res["output"])

    def test_03_dangerous_patterns_blocked(self):
        destructive_cmds = [
            "rm -rf /",
            "rm -r ~",
            "mkfs.ext4 /dev/sda1"
        ]
        for cmd in destructive_cmds:
            res = secure_execute(cmd)
            self.assertFalse(res["success"])
            self.assertIn("SECURITY EXCEPTION", res["output"])

    def test_04_empty_and_invalid_commands(self):
        res_empty = secure_execute("   ")
        self.assertFalse(res_empty["success"])

    def test_05_audit_trail_logging(self):
        secure_execute("echo 'audit_verification_marker'")
        self.assertTrue(os.path.exists(SANDBOX_LOG))
        with open(SANDBOX_LOG, "r") as f:
            content = f.read()
        self.assertIn("audit_verification_marker", content)

if __name__ == "__main__":
    unittest.main()
