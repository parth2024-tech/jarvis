import asyncio
import hashlib
import os
import subprocess

import edge_tts

JARVIS_DIR = "/home/thor/Desktop/JARVIS"
CACHE_DIR = os.path.join(JARVIS_DIR, "memory", "tts_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

VOICE_PROFILES = {
    "alexa": {
        "id": "en-US-JennyNeural",
        "name": "Alexa (US Natural)",
        "gender": "Female",
        "description": "Warm, clear, natural American conversational assistant (Amazon Alexa signature tone)",
        "rate": "+0%",
        "pitch": "+0Hz"
    },
    "alexa_aria": {
        "id": "en-US-AriaNeural",
        "name": "Alexa Expressive (US)",
        "gender": "Female",
        "description": "Confident, positive, highly expressive American assistant",
        "rate": "+0%",
        "pitch": "+0Hz"
    },
    "jarvis": {
        "id": "en-GB-RyanNeural",
        "name": "J.A.R.V.I.S. (UK Butler)",
        "gender": "Male",
        "description": "Sophisticated, calm, respectful British butler diction",
        "rate": "+0%",
        "pitch": "-2Hz"
    },
    "friday": {
        "id": "en-GB-SoniaNeural",
        "name": "F.R.I.D.A.Y. (UK Assistant)",
        "gender": "Female",
        "description": "Polite, sharp, high-clarity British female AI assistant",
        "rate": "+0%",
        "pitch": "+0Hz"
    }
}

DEFAULT_PROFILE = "alexa"

def get_cache_path(text: str, voice_id: str, rate: str) -> str:
    key = f"{text.strip()}:{voice_id}:{rate}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"{h}.mp3")

async def synthesize_speech(text: str, voice_key: str = DEFAULT_PROFILE, rate: str = "+0%") -> bytes:
    """
    Synthesizes text into high-fidelity neural MP3 audio using Microsoft Neural voices.
    Caches audio to disk to achieve sub-millisecond retrieval on repeated phrases.
    """
    clean_text = text.strip()
    if not clean_text:
        return b""

    profile = VOICE_PROFILES.get(voice_key, VOICE_PROFILES[DEFAULT_PROFILE])
    voice_id = profile["id"]
    cache_file = get_cache_path(clean_text, voice_id, rate)

    # Check cache
    if os.path.exists(cache_file) and os.path.getsize(cache_file) > 0:
        with open(cache_file, "rb") as f:
            return f.read()

    # Synthesize via edge_tts
    try:
        communicate = edge_tts.Communicate(clean_text, voice_id, rate=rate)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        audio_bytes = b"".join(chunks)

        if audio_bytes:
            with open(cache_file, "wb") as f:
                f.write(audio_bytes)
        return audio_bytes
    except Exception as e:
        print(f"[VOICE ENGINE ERROR] Failed to synthesize speech: {e}")
        return b""

def play_speech_locally(text: str, voice_key: str = DEFAULT_PROFILE) -> bool:
    """
    Synthesizes and immediately plays audio through the PC's primary audio sink (mpv / ffplay).
    """
    try:
        audio_bytes = asyncio.run(synthesize_speech(text, voice_key))
        if not audio_bytes:
            return False

        profile = VOICE_PROFILES.get(voice_key, VOICE_PROFILES[DEFAULT_PROFILE])
        cache_file = get_cache_path(text, profile["id"], "+0%")

        # Play using mpv if available, fallback to ffplay
        player = None
        if os.path.exists("/usr/bin/mpv"):
            player = ["/usr/bin/mpv", "--no-video", "--really-quiet", cache_file]
        elif os.path.exists("/usr/bin/ffplay"):
            player = ["/usr/bin/ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", cache_file]

        if player:
            subprocess.run(player, check=False)
            return True
        return False
    except Exception as e:
        print(f"[VOICE PLAYBACK ERROR] {e}")
        return False

def get_voice_profiles() -> dict:
    return VOICE_PROFILES
