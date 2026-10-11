import unittest
import sys

sys.path.append("/home/thor/Desktop/JARVIS/core")
from network_tools import get_network_status, ping_latency

class TestNetworkTools(unittest.TestCase):
    def test_get_network_status(self):
        res = get_network_status()
        self.assertTrue(res["success"])
        self.assertIn("local_ip", res)
        self.assertIn("summary", res)
        self.assertIn("bytes_sent_mb", res)

    def test_ping_latency(self):
        res = ping_latency("1.1.1.1")
        self.assertIn("success", res)
        self.assertIn("summary", res)

if __name__ == "__main__":
    unittest.main()
