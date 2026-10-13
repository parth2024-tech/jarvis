import sys
import unittest

sys.path.append("/home/thor/Desktop/JARVIS/core")
from power_display import get_brightness, get_power_status


class TestPowerDisplay(unittest.TestCase):
    def test_get_brightness(self):
        res = get_brightness()
        self.assertIn("success", res)
        self.assertIn("percent", res)
        self.assertGreaterEqual(res["percent"], 0)
        self.assertLessEqual(res["percent"], 100)

    def test_get_power_status(self):
        res = get_power_status()
        self.assertTrue(res["success"])
        self.assertIn("has_battery", res)
        self.assertIn("status_text", res)

if __name__ == "__main__":
    unittest.main()
