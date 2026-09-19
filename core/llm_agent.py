import re
import time
import requests
import json
from system_telemetry import get_telemetry_summary, get_system_metrics
from media_controller import set_volume, change_volume, toggle_mute, get_volume, control_playback, get_playback_info
from app_controller import launch_app, send_notification
from vision import capture_screen_state
from vector_memory import store_memory, query_memories, get_relevant_context
from sandbox import secure_execute

OLLAMA_GEN_URL = "http://127.0.0.1:11434/api/generate"
PRIMARY_MODEL = "llama3.2:latest"
FALLBACK_MODEL = "qwen3:4b-fast"

JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), Tony Stark's personal autonomous AI operating layer.
You speak with refined British diction, calm precision, subtle dry wit, and unwavering loyalty.
Always address the user as 'Sir'. Keep responses concise (1 to 2 sentences) so they are crisp and natural for voice synthesis over the Stark HUD.
Never use robotic meta-commentary. Speak directly and characteristically as J.A.R.V.I.S."""

def clean_llm_response(text: str) -> str:
    """Removes thinking tags and extra formatting."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    # Remove surrounding quotes if model added them
    if cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1].strip()
    return cleaned

def execute_agent_directive(query: str, context: str = "hud") -> dict:
    """
    Main cognitive router and executive agent for J.A.R.V.I.S.
    Analyzes user directives, dispatches OS/hardware tools, queries memory,
    and returns styled natural language responses.
    """
    start_time = time.time()
    q_clean = query.strip()
    q_lower = q_clean.lower()
    
    intent = "general_cognition"
    tool_result = None
    response = ""

    # ==========================================
    # Fast Tool Routing: Audio & Media
    # ==========================================
    if "mute" in q_lower or "unmute" in q_lower:
        intent = "media_control"
        tool_result = toggle_mute()
        response = tool_result.get("message", "Audio toggle executed, Sir.")

    elif "volume up" in q_lower or "louder" in q_lower or "increase volume" in q_lower:
        intent = "media_control"
        tool_result = change_volume(+10)
        response = tool_result.get("message", "Volume increased by 10%, Sir.")

    elif "volume down" in q_lower or "quieter" in q_lower or "decrease volume" in q_lower or "lower volume" in q_lower:
        intent = "media_control"
        tool_result = change_volume(-10)
        response = tool_result.get("message", "Volume decreased by 10%, Sir.")

    elif "volume to" in q_lower or "set volume" in q_lower:
        intent = "media_control"
        match = re.search(r"(\d+)\s*(?:%|percent)?", q_lower)
        target = int(match.group(1)) if match else 50
        tool_result = set_volume(target)
        response = tool_result.get("message", f"Volume configured to {target}%, Sir.")

    elif any(k in q_lower for k in ["pause music", "resume music", "play music", "next track", "skip track", "previous track"]):
        intent = "media_control"
        if "next" in q_lower or "skip" in q_lower:
            tool_result = control_playback("next")
        elif "previous" in q_lower:
            tool_result = control_playback("previous")
        elif "pause" in q_lower:
            tool_result = control_playback("pause")
        elif "play" in q_lower or "resume" in q_lower:
            tool_result = control_playback("play")
        else:
            tool_result = control_playback("play-pause")
        response = tool_result.get("message", "Playback updated, Sir.")

    # ==========================================
    # Fast Tool Routing: Screen Capture / Vision
    # ==========================================
    elif any(k in q_lower for k in ["screenshot", "capture screen", "screen state", "look at screen", "visual scan"]):
        intent = "multimodal_vision"
        vis = capture_screen_state()
        tool_result = vis
        if vis["success"]:
            response = f"Desktop telemetry captured at {vis['width']} by {vis['height']} resolution, Sir. Frame stored to visual memory."
        else:
            response = f"Visual capture sensor reported an anomaly: {vis.get('error', 'unknown')}, Sir."

    # ==========================================
    # Fast Tool Routing: Desktop Applications
    # ==========================================
    elif "open terminal" in q_lower or "launch terminal" in q_lower or "open kitty" in q_lower:
        intent = "application_control"
        tool_result = launch_app("terminal")
        response = "Terminal initialized on primary display, Sir."

    elif "open editor" in q_lower or "open code" in q_lower or "launch vs code" in q_lower:
        intent = "application_control"
        tool_result = launch_app("code")
        response = "Visual Studio Code environment opened, Sir."

    elif "open browser" in q_lower or "launch browser" in q_lower:
        intent = "application_control"
        tool_result = launch_app("browser")
        response = "Web browser interface engaged, Sir."

    elif "notify" in q_lower or "alert desktop" in q_lower:
        intent = "application_control"
        msg = q_clean.replace("notify", "").replace("alert desktop", "").strip() or "Protocol updated."
        send_notification("DIRECTIVE ACKNOWLEDGED", msg)
        response = f"Desktop notification dispatched, Sir."

    # ==========================================
    # Fast Tool Routing: Memory Storage & Recall
    # ==========================================
    elif q_lower.startswith("remember that ") or q_lower.startswith("store memory ") or q_lower.startswith("note that "):
        intent = "memory_storage"
        fact = re.sub(r"^(remember that|store memory|note that)\s+", "", q_clean, flags=re.IGNORECASE).strip()
        mem_res = store_memory(fact, category="user_protocol")
        tool_result = mem_res
        response = f"Stored in long-term vector memory: '{fact}', Sir."

    # ==========================================
    # Fast Tool Routing: Hardware & Diagnostics
    # ==========================================
    elif any(k in q_lower for k in ["diagnostic", "system health", "hardware status", "reactor status", "cpu status", "telemetry status"]):
        intent = "system_diagnostic"
        response = get_telemetry_summary()

    # ==========================================
    # Fast Tool Routing: Temporal queries
    # ==========================================
    elif "what time" in q_lower or "current time" in q_lower:
        intent = "temporal_query"
        response = f"Local temporal coordinates are {time.strftime('%H:%M:%S on %A, %B %d')}, Sir."

    # ==========================================
    # LLM Reasoning & Semantic Memory Synthesis
    # ==========================================
    if not response:
        # Retrieve vector memory context
        recalled_context = get_relevant_context(q_clean, top_k=2)
        metrics = get_system_metrics()

        prompt_payload = f"""{JARVIS_SYSTEM_PROMPT}

CURRENT SYSTEM TELEMETRY:
- Reactor Stability: {metrics['reactor_stability']}%
- CPU Load: {metrics['cpu_percent']}% across {metrics['cpu_count']} cores
- Memory: {metrics['ram_percent']}% utilized ({metrics['ram_used_gb']} GB / {metrics['ram_total_gb']} GB)
- Storage: {metrics['disk_free_gb']} GB free

{recalled_context}

USER DIRECTIVE: {q_clean}

RESPONSE (As J.A.R.V.I.S.):"""

        # Call local Ollama LLM
        llm_text = ""
        for model in [PRIMARY_MODEL, FALLBACK_MODEL]:
            try:
                res = requests.post(
                    OLLAMA_GEN_URL,
                    json={
                        "model": model,
                        "prompt": prompt_payload,
                        "stream": False,
                        "options": {
                            "temperature": 0.6,
                            "top_p": 0.9,
                            "num_predict": 120
                        }
                    },
                    timeout=12
                )
                if res.status_code == 200:
                    raw_text = res.json().get("response", "")
                    llm_text = clean_llm_response(raw_text)
                    if llm_text:
                        break
            except Exception:
                continue

        if llm_text:
            response = llm_text
        else:
            # High-assurance graceful fallback
            response = f"At your service, Sir. All industrial subsystems remain synchronized at {metrics['reactor_stability']}% stability."

    latency = round((time.time() - start_time) * 1000, 2)
    return {
        "status": "success",
        "intent": intent,
        "response": response,
        "tool_result": tool_result,
        "latency_ms": latency
    }
