import unittest
import requests
import time
import subprocess
import sys

class TestJarvisUnifiedCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["pkill", "-f", "server.py"], capture_output=True)
        time.sleep(1)
        cls.server_process = subprocess.Popen(
            [sys.executable, "server.py"],
            cwd="/home/thor/Desktop/JARVIS/core",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        # Wait up to 10 seconds for port 8080 to be ready
        ready = False
        for _ in range(20):
            try:
                res = requests.get("http://127.0.0.1:8080/api/telemetry", timeout=1)
                if res.status_code == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(0.5)
        if not ready:
            raise RuntimeError("Server failed to start on port 8080")

    @classmethod
    def tearDownClass(cls):
        cls.server_process.terminate()
        cls.server_process.wait()

    def test_01_telemetry_endpoint(self):
        res = requests.get("http://127.0.0.1:8080/api/telemetry")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reactor_stability", data)
        self.assertIn("WEBSOCKET", data["neural_mesh"])

    def test_02_command_diagnostic(self):
        payload = {"query": "system diagnostic check", "context": "hud"}
        res = requests.post("http://127.0.0.1:8080/api/command", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["intent"], "system_diagnostic")

    def test_03_secure_execution_sandbox(self):
        payload = {"query": "run test suite", "context": "hud"}
        res = requests.post("http://127.0.0.1:8080/api/command", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "secure_execution")
        self.assertIn("Sandbox execution completed", data["response"])

    def test_04_sandbox_security_violation_block(self):
        sys.path.append("/home/thor/Desktop/JARVIS/core")
        from sandbox import secure_execute
        
        res = secure_execute("rm -rf /")
        self.assertFalse(res["success"])
        self.assertIn("SECURITY EXCEPTION", res["output"])

        res2 = secure_execute("mkfs.ext4 /dev/sda1")
        self.assertFalse(res2["success"])
        self.assertIn("SECURITY EXCEPTION", res2["output"])

if __name__ == "__main__":
    unittest.main()
