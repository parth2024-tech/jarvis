import subprocess
import re
import psutil
from sandbox import secure_execute

def get_brightness() -> dict:
    """
    Retrieves current display brightness percentage and raw values using brightnessctl.
    """
    try:
        curr_res = subprocess.run(["brightnessctl", "get"], capture_output=True, text=True, timeout=2)
        max_res = subprocess.run(["brightnessctl", "max"], capture_output=True, text=True, timeout=2)

        curr = int(curr_res.stdout.strip())
        max_val = int(max_res.stdout.strip())
        pct = round((curr / max_val) * 100) if max_val > 0 else 50

        return {
            "success": True,
            "percent": pct,
            "current": curr,
            "max": max_val
        }
    except Exception as e:
        return {"success": False, "error": str(e), "percent": 50}

def set_brightness(percent: int) -> dict:
    """
    Sets display brightness to a specific percentage (1% to 100%).
    """
    clamped = max(1, min(100, int(percent)))
    cmd = f"brightnessctl set {clamped}%"
    res = secure_execute(cmd)
    if res["success"]:
        return {"success": True, "percent": clamped, "message": f"Display illumination calibrated to {clamped}%, Sir."}
    return {"success": False, "error": res.get("output", "Failed to adjust brightness")}

def change_brightness(delta: int) -> dict:
    """
    Increases or decreases display brightness by delta percentage.
    """
    sign = "+" if delta >= 0 else "-"
    abs_val = abs(int(delta))
    cmd = f"brightnessctl set {abs_val}%{sign}"
    res = secure_execute(cmd)
    if res["success"]:
        curr = get_brightness()
        return {"success": True, "percent": curr["percent"], "message": f"Display brightness adjusted by {sign}{abs_val}%. Currently at {curr['percent']}%, Sir."}
    return {"success": False, "error": res.get("output", "Failed to shift brightness")}

def lock_session() -> dict:
    """
    Secures the active desktop workstation by locking the session via loginctl.
    """
    res = secure_execute("loginctl lock-session")
    if res["success"]:
        return {"success": True, "message": "Workstation perimeter secured. Display session locked, Sir."}
    return {"success": False, "error": res.get("output", "Failed to lock session")}

def get_power_status() -> dict:
    """
    Returns battery charge, power source, and estimated runtime.
    """
    bat = psutil.sensors_battery()
    if bat is None:
        return {
            "success": True,
            "has_battery": False,
            "status_text": "Host machine running on primary AC utility power, Sir."
        }

    plugged = bat.power_plugged
    pct = round(bat.percent, 1)
    status_str = "charging on AC power" if plugged else "discharging on auxiliary battery"
    time_str = ""
    if bat.secsleft > 0 and bat.secsleft != psutil.POWER_TIME_UNLIMITED:
        hours = bat.secsleft // 3600
        mins = (bat.secsleft % 3600) // 60
        time_str = f" (~{hours}h {mins}m remaining)"

    return {
        "success": True,
        "has_battery": True,
        "percent": pct,
        "plugged": plugged,
        "secsleft": bat.secsleft,
        "status_text": f"Auxiliary power cell at {pct}% ({status_str}){time_str}, Sir."
    }
