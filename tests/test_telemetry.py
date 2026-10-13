import sys
import unittest

sys.path.append("/home/thor/Desktop/JARVIS/core")
from system_telemetry import get_system_metrics, get_telemetry_summary


class TestSystemTelemetry(unittest.TestCase):
    def test_metrics_structure(self):
        m = get_system_metrics()
        self.assertIn("reactor_stability", m)
        self.assertIn("cpu_percent", m)
        self.assertIn("ram_percent", m)
        self.assertIn("disk_free_gb", m)
        self.assertGreaterEqual(m["reactor_stability"], 50.0)
        self.assertLessEqual(m["reactor_stability"], 100.0)

    def test_telemetry_summary_contains_key_elements(self):
        summary = get_telemetry_summary()
        self.assertIn("Reactor stability is at", summary)
        self.assertIn("CPU load is", summary)
        self.assertIn("Memory utilization stands at", summary)

if __name__ == "__main__":
    unittest.main()
