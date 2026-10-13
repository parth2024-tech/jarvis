import sys
import unittest

sys.path.append("/home/thor/Desktop/JARVIS/core")
from vector_memory import get_relevant_context, query_memories, store_memory


class TestVectorMemory(unittest.TestCase):
    def test_store_and_query_memory(self):
        res = store_memory("Stark Industries clean energy initiative test.", category="test")
        self.assertTrue(res["success"])
        self.assertIn("id", res)

        recalled = query_memories("clean energy", top_k=3, min_similarity=0.2)
        self.assertIsInstance(recalled, list)

    def test_get_relevant_context_formatting(self):
        store_memory("Protocol 11: Emergency defense systems ready.", category="defense")
        ctx = get_relevant_context("emergency defense", top_k=2)
        self.assertIsInstance(ctx, str)

if __name__ == "__main__":
    unittest.main()
