import re
import subprocess

from sandbox import secure_execute


def get_volume() -> dict:
    """
    Returns current master volume percentage and mute state using pactl.
    """
    try:
        res = subprocess.run(
            ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
            capture_output=True, text=True, timeout=3
        )
        volume_match = re.search(r"(\d+)%", res.stdout)
        volume_pct = int(volume_match.group(1)) if volume_match else 50

        mute_res = subprocess.run(
            ["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
            capture_output=True, text=True, timeout=3
        )
        is_muted = "yes" in mute_res.stdout.lower()

        return {
            "success": True,
            "volume_percent": volume_pct,
            "is_muted": is_muted
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "volume_percent": 50,
            "is_muted": False
        }

def set_volume(percent: int) -> dict:
    """
    Sets master audio volume to a specific percentage (0 - 100).
    """
    clamped = max(0, min(100, percent))
    cmd = f"pactl set-sink-volume @DEFAULT_SINK@ {clamped}%"
    res = secure_execute(cmd)
    if res["success"]:
        return {"success": True, "message": f"Master audio volume adjusted to {clamped}%, Sir."}
    return {"success": False, "error": res.get("output", "Volume control failed")}

def change_volume(delta: int) -> dict:
    """
    Increases or decreases volume by delta percentage (e.g. +10, -10).
    """
    sign = "+" if delta >= 0 else "-"
    abs_delta = abs(delta)
    cmd = f"pactl set-sink-volume @DEFAULT_SINK@ {sign}{abs_delta}%"
    res = secure_execute(cmd)
    if res["success"]:
        curr = get_volume()
        return {"success": True, "message": f"Volume modified by {sign}{abs_delta}%. Currently at {curr['volume_percent']}%, Sir."}
    return {"success": False, "error": res.get("output", "Volume adjustment failed")}

def toggle_mute() -> dict:
    """
    Toggles master audio mute state.
    """
    res = secure_execute("pactl set-sink-mute @DEFAULT_SINK@ toggle")
    if res["success"]:
        curr = get_volume()
        state = "muted" if curr["is_muted"] else "unmuted"
        return {"success": True, "message": f"Audio output has been {state}, Sir."}
    return {"success": False, "error": res.get("output", "Mute toggle failed")}

def control_playback(action: str) -> dict:
    """
    Controls media playback via playerctl: play-pause, next, previous, stop.
    """
    valid_actions = {
        "play": "play",
        "pause": "pause",
        "play-pause": "play-pause",
        "toggle": "play-pause",
        "next": "next",
        "previous": "previous",
        "prev": "previous",
        "stop": "stop"
    }
    act = valid_actions.get(action.lower().strip(), "play-pause")
    cmd = f"playerctl {act}"
    res = secure_execute(cmd)
    if res["success"]:
        return {"success": True, "message": f"Media playback command '{act}' executed, Sir."}
    else:
        # Playerctl exits non-zero if no media player is currently running
        return {"success": True, "message": f"Playback signal '{act}' dispatched (no active media player detected), Sir."}

def get_playback_info() -> dict:
    """
    Retrieves current playing track artist and title via playerctl.
    """
    try:
        res = subprocess.run(
            ["playerctl", "metadata", "--format", "{{artist}} - {{title}}"],
            capture_output=True, text=True, timeout=3
        )
        if res.returncode == 0 and res.stdout.strip():
            return {"success": True, "now_playing": res.stdout.strip()}
        return {"success": True, "now_playing": "No media currently playing"}
    except Exception:
        return {"success": False, "now_playing": "Media player inactive"}
