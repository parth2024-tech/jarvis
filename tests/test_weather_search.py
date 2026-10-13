import sys
import unittest

sys.path.append("/home/thor/Desktop/JARVIS/core")
from weather_search import get_weather, search_instant_knowledge


class TestWeatherSearch(unittest.TestCase):
    def test_get_weather(self):
        res = get_weather("London")
        self.assertIn("success", res)
        self.assertIn("summary", res)
        if res["success"] and "temp_c" in res:
            self.assertIsNotNone(res["temp_c"])

    def test_search_instant_knowledge(self):
        res = search_instant_knowledge("Python programming language")
        self.assertIn("success", res)
        self.assertIn("summary", res)

if __name__ == "__main__":
    unittest.main()
