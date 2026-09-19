import unittest
import sys
import os

sys.path.append("/home/thor/Desktop/JARVIS/core")
from vision import capture_screen_state

class TestVision(unittest.TestCase):
    def test_screen_capture_execution(self):
        res = capture_screen_state()
        self.assertIn("success", res)
        self.assertIn("duration_ms", res)
        if res["success"]:
            self.assertTrue(os.path.exists(res["path"]))
            self.assertGreater(res["width"], 0)
            self.assertGreater(res["height"], 0)

if __name__ == "__main__":
    unittest.main()
