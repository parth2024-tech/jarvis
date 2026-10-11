import shutil
import os
import requests

def probe_system_capabilities() -> dict:
    """
    Scans the host system for required runtime utilities and protocols,
    producing an authoritative capability and degradation report.
    """
    env_wayland = os.environ.get("WAYLAND_DISPLAY")
    session_type = os.environ.get("XDG_SESSION_TYPE", "unknown")
    is_wayland = bool(env_wayland or session_type == "wayland")

    tools = {
        "screen_capture": {
            "spectacle": bool(shutil.which("spectacle")),
            "grim": bool(shutil.which("grim")),
            "available": bool(shutil.which("spectacle") or shutil.which("grim"))
        },
        "optical_ocr": {
            "tesseract": bool(shutil.which("tesseract")),
            "available": bool(shutil.which("tesseract"))
        },
        "display_backlight": {
            "brightnessctl": bool(shutil.which("brightnessctl")),
            "available": bool(shutil.which("brightnessctl"))
        },
        "clipboard": {
            "wl_copy": bool(shutil.which("wl-copy")),
            "wl_paste": bool(shutil.which("wl-paste")),
            "available": bool(shutil.which("wl-copy") and shutil.which("wl-paste"))
        },
        "media_audio": {
            "pactl": bool(shutil.which("pactl")),
            "playerctl": bool(shutil.which("playerctl")),
            "available": bool(shutil.which("pactl"))
        },
        "notifications": {
            "notify_send": bool(shutil.which("notify-send")),
            "available": bool(shutil.which("notify-send"))
        },
        "session_lock": {
            "loginctl": bool(shutil.which("loginctl")),
            "qdbus": bool(shutil.which("qdbus")),
            "available": bool(shutil.which("loginctl") or shutil.which("qdbus"))
        },
        "network": {
            "nmcli": bool(shutil.which("nmcli")),
            "ping": bool(shutil.which("ping")),
            "available": True
        }
    }

    # Check local Ollama health
    ollama_online = False
    ollama_models = []
    try:
        res = requests.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
        if res.status_code == 200:
            ollama_online = True
            models_data = res.json().get("models", [])
            ollama_models = [m.get("name") for m in models_data]
    except Exception:
        ollama_online = False

    degraded_features = []
    if not tools["screen_capture"]["available"]:
        degraded_features.append("Screen capture unavailable (requires spectacle or grim)")
    if not tools["optical_ocr"]["available"]:
        degraded_features.append("Screen OCR unavailable (requires tesseract)")
    if not tools["display_backlight"]["available"]:
        degraded_features.append("Hardware brightness control unavailable (requires brightnessctl)")
    if not tools["clipboard"]["available"]:
        degraded_features.append("Wayland clipboard bridge unavailable (requires wl-clipboard)")
    if not ollama_online:
        degraded_features.append("Local cognitive LLM offline (requires Ollama service)")

    status = "nominal" if not degraded_features else ("degraded" if ollama_online else "critical_offline")

    return {
        "status": status,
        "is_wayland": is_wayland,
        "session_type": session_type,
        "ollama_online": ollama_online,
        "ollama_models": ollama_models,
        "subsystems": tools,
        "degraded_features": degraded_features,
        "degraded_count": len(degraded_features)
    }

CAPABILITIES = probe_system_capabilities()
