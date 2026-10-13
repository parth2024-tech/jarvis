import sys
import time
import unittest

sys.path.append("/home/thor/Desktop/JARVIS/core")
from heartbeat import ProactiveHeartbeat


class TestHeartbeat(unittest.TestCase):
    def test_heartbeat_lifecycle(self):
        hb = ProactiveHeartbeat(interval_seconds=1)
        hb.start()
        self.assertTrue(hb.running)
        time.sleep(1.5)
        hb.stop()
        self.assertFalse(hb.running)

if __name__ == "__main__":
    unittest.main()
