import unittest
import requests
import time
import subprocess
import sys

sys.path.append("/home/thor/Desktop/JARVIS/core")
from security_guard import get_or_create_auth_token

AUTH_TOKEN = get_or_create_auth_token()
AUTH_HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}

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
        # Wait up to 10 seconds for port 8090 to be ready
        ready = False
        for _ in range(20):
            try:
                res = requests.get("http://127.0.0.1:8090/api/health", timeout=1)
                if res.status_code == 200:
                    ready = True
                    break
            except Exception:
                time.sleep(0.5)
        if not ready:
            raise RuntimeError("Server failed to start on port 8090")

    @classmethod
    def tearDownClass(cls):
        cls.server_process.terminate()
        cls.server_process.wait()

    def test_01_health_and_telemetry_endpoints(self):
        # Health probe is public
        res_health = requests.get("http://127.0.0.1:8090/api/health")
        self.assertEqual(res_health.status_code, 200)
        self.assertEqual(res_health.json()["status"], "healthy")

        # Telemetry requires authentication
        res_unauth = requests.get("http://127.0.0.1:8090/api/telemetry")
        self.assertEqual(res_unauth.status_code, 401)

        # Authenticated telemetry
        res = requests.get("http://127.0.0.1:8090/api/telemetry", headers=AUTH_HEADERS)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reactor_stability", data)
        self.assertIn("WEBSOCKET", data["neural_mesh"])

    def test_01b_unauthenticated_request_rejected(self):
        # Sensitive endpoint without auth token must return 401
        res = requests.post("http://127.0.0.1:8090/api/command", json={"query": "ping", "context": "hud"})
        self.assertEqual(res.status_code, 401)


    def test_02_command_diagnostic(self):
        payload = {"query": "system diagnostic check", "context": "hud"}
        res = requests.post("http://127.0.0.1:8090/api/command", json=payload, headers=AUTH_HEADERS)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["intent"], "system_diagnostic")

    def test_03_secure_execution_sandbox(self):
        payload = {"query": "run test suite", "context": "hud"}
        res = requests.post("http://127.0.0.1:8090/api/command", json=payload, headers=AUTH_HEADERS)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "secure_execution")
        self.assertIn("Sandbox execution completed", data["response"])

    def test_04_sandbox_security_violation_block(self):
        from sandbox import secure_execute
        
        res = secure_execute("rm -rf /")
        self.assertFalse(res["success"])
        self.assertIn("SECURITY EXCEPTION", res["output"])

        res2 = secure_execute("mkfs.ext4 /dev/sda1")
        self.assertFalse(res2["success"])
        self.assertIn("SECURITY EXCEPTION", res2["output"])

    def test_05_productivity_todos_endpoints(self):
        # Create todo
        res = requests.post("http://127.0.0.1:8090/api/productivity/todos", json={"task": "Stark Industrial Check", "priority": "high"}, headers=AUTH_HEADERS)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        todo_id = data["id"]

        # List todos
        res_list = requests.get("http://127.0.0.1:8090/api/productivity/todos", headers=AUTH_HEADERS)
        self.assertEqual(res_list.status_code, 200)
        todos = res_list.json()["todos"]
        self.assertTrue(any(t["id"] == todo_id for t in todos))

        # Complete todo
        res_comp = requests.post(f"http://127.0.0.1:8090/api/productivity/todos/{todo_id}/complete", headers=AUTH_HEADERS)
        self.assertEqual(res_comp.status_code, 200)

    def test_06_productivity_timers_endpoints(self):
        # Create timer
        res = requests.post("http://127.0.0.1:8090/api/productivity/timers", json={"seconds": 15, "label": "Test Unified Timer"}, headers=AUTH_HEADERS)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        timer_id = data["timer_id"]

        # List timers
        res_list = requests.get("http://127.0.0.1:8090/api/productivity/timers", headers=AUTH_HEADERS)
        self.assertEqual(res_list.status_code, 200)
        timers = res_list.json()["timers"]
        self.assertTrue(any(t["id"] == timer_id for t in timers))

        # Cancel timer
        res_del = requests.delete(f"http://127.0.0.1:8090/api/productivity/timers/{timer_id}", headers=AUTH_HEADERS)
        self.assertEqual(res_del.status_code, 200)

    def test_07_system_display_brightness_endpoint(self):
        res = requests.get("http://127.0.0.1:8090/api/system/brightness", headers=AUTH_HEADERS)
        self.assertEqual(res.status_code, 200)
        self.assertIn("percent", res.json())

    def test_08_weather_and_network_endpoints(self):
        res_net = requests.get("http://127.0.0.1:8090/api/network/status", headers=AUTH_HEADERS)
        self.assertEqual(res_net.status_code, 200)
        self.assertTrue(res_net.json()["success"])

        res_ping = requests.post("http://127.0.0.1:8090/api/network/ping", json={"host": "1.1.1.1"}, headers=AUTH_HEADERS)
        self.assertEqual(res_ping.status_code, 200)
        self.assertIn("summary", res_ping.json())

        res_weather = requests.get("http://127.0.0.1:8090/api/weather", headers=AUTH_HEADERS)
        self.assertEqual(res_weather.status_code, 200)
        self.assertIn("summary", res_weather.json())

    def test_09_system_capabilities_endpoint(self):
        res = requests.get("http://127.0.0.1:8090/api/system/capabilities", headers=AUTH_HEADERS)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("subsystems", data)
        self.assertIn("status", data)

if __name__ == "__main__":
    unittest.main()
