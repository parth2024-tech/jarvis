import os
import sys
import time
import argparse

JARVIS_DIR = "/home/thor/Desktop/JARVIS"
sys.path.append(os.path.join(JARVIS_DIR, "core"))

from voice_engine import play_speech_locally, get_voice_profiles
from llm_agent import execute_agent_directive
from system_telemetry import get_telemetry_summary

def run_alexa_cli(voice_profile: str = "alexa"):
    """
    Interactive standalone PC voice assistant loop.
    Speaks responses out loud on the host machine using neural voice synthesis.
    """
    profiles = get_voice_profiles()
    selected = profiles.get(voice_profile, profiles["alexa"])
    
    print("\n" + "="*60)
    print("   🎙️  ALEXA / J.A.R.V.I.S. VOICE ASSISTANT FOR PC")
    print(f"   Voice: {selected['name']} ({selected['description']})")
    print("="*60)
    
    greeting = f"Hello! I am your PC voice assistant. How can I help you today?"
    print(f"\n[ALEXA] {greeting}")
    play_speech_locally(greeting, voice_profile)

    while True:
        try:
            user_input = input("\n[YOU >] ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "stop", "bye"]:
                farewell = "Goodbye! Have a great day."
                print(f"[ALEXA] {farewell}")
                play_speech_locally(farewell, voice_profile)
                break

            result = execute_agent_directive(user_input)
            response_text = result["response"]
            
            print(f"[ALEXA] {response_text}")
            print(f"        (Intent: {result['intent']} | Latency: {result['latency_ms']}ms)")
            play_speech_locally(response_text, voice_profile)
        except (KeyboardInterrupt, EOFError):
            print("\nShutting down voice assistant.")
            break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alexa / J.A.R.V.I.S. PC Voice Assistant")
    parser.add_argument("--voice", default="alexa", choices=["alexa", "alexa_aria", "jarvis", "friday"],
                        help="Neural voice profile to use")
    parser.add_argument("--say", type=str, help="Speak a one-off phrase out loud and exit")
    args = parser.parse_args()

    if args.say:
        play_speech_locally(args.say, args.voice)
    else:
        run_alexa_cli(args.voice)
