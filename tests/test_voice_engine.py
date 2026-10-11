import unittest
import sys
import asyncio
import os

sys.path.append("/home/thor/Desktop/JARVIS/core")
from voice_engine import get_voice_profiles, synthesize_speech

class TestVoiceEngine(unittest.TestCase):
    def test_voice_profiles_exist(self):
        profiles = get_voice_profiles()
        self.assertIn("alexa", profiles)
        self.assertIn("jarvis", profiles)
        self.assertIn("friday", profiles)
        self.assertEqual(profiles["alexa"]["id"], "en-US-JennyNeural")

    def test_synthesis_returns_bytes(self):
        async def run_syn():
            audio = await synthesize_speech("Test tone check.", voice_key="alexa")
            return audio
        data = asyncio.run(run_syn())
        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)

if __name__ == "__main__":
    unittest.main()
