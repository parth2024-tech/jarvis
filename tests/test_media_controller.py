import unittest
import sys

sys.path.append("/home/thor/Desktop/JARVIS/core")
from media_controller import get_volume, set_volume, toggle_mute, control_playback, get_playback_info

class TestMediaController(unittest.TestCase):
    def test_get_volume_returns_structure(self):
        v = get_volume()
        self.assertIn("success", v)
        self.assertIn("volume_percent", v)
        self.assertIn("is_muted", v)

    def test_set_volume_safe_range(self):
        res = set_volume(75)
        self.assertIn("success", res)

    def test_playback_controls_safe(self):
        res = control_playback("play-pause")
        self.assertTrue(res["success"])

    def test_playback_info_safe(self):
        info = get_playback_info()
        self.assertIn("now_playing", info)

if __name__ == "__main__":
    unittest.main()
