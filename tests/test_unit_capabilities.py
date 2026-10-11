import unittest
import sys

sys.path.append("/home/thor/Desktop/JARVIS/core")
from system_capabilities import probe_system_capabilities

class TestSystemCapabilities(unittest.TestCase):
    def test_capabilities_structure(self):
        caps = probe_system_capabilities()
        self.assertIn("status", caps)
        self.assertIn("is_wayland", caps)
        self.assertIn("session_type", caps)
        self.assertIn("ollama_online", caps)
        self.assertIn("ollama_models", caps)
        self.assertIn("subsystems", caps)
        self.assertIn("degraded_features", caps)
        self.assertIn("degraded_count", caps)
        self.assertIn(caps["status"], ["nominal", "degraded"])

    def test_subsystems_matrix(self):
        caps = probe_system_capabilities()
        subsystems = caps["subsystems"]
        expected_subsystems = [
            "screen_capture", "optical_ocr", "display_backlight",
            "clipboard", "media_audio", "notifications",
            "session_lock", "network"
        ]
        for sub in expected_subsystems:
            self.assertIn(sub, subsystems)
            self.assertIn("available", subsystems[sub])

    def test_ollama_status(self):
        caps = probe_system_capabilities()
        self.assertIsInstance(caps["ollama_online"], bool)
        self.assertIsInstance(caps["ollama_models"], list)

if __name__ == "__main__":
    unittest.main()
