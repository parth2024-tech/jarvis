import shutil
import subprocess

import psutil


def get_brightness() -> dict:
    """
    Retrieves current display brightness percentage, raw values,
    and active hardware device using brightnessctl machine-readable output.
    """
    if not shutil.which("brightnessctl"):
        return {
            "success": False,
            "error": "brightnessctl utility not installed",
            "percent": 50,
            "device": "unknown"
        }

    try:
        # -m prints machine readable format: device,class,curr,pct%,max
        res = subprocess.run(["brightnessctl", "-m"], capture_output=True, text=True, timeout=2.0)
        if res.returncode == 0 and res.stdout.strip():
            first_line = res.stdout.strip().splitlines()[0]
            parts = first_line.split(",")
            device_name = parts[0]
            pct_str = parts[3].replace("%", "") if len(parts) > 3 else "50"
            pct = int(pct_str)
            curr = int(parts[2]) if len(parts) > 2 else 0
            max_val = int(parts[4]) if len(parts) > 4 else 100
            return {
                "success": True,
                "percent": pct,
                "current": curr,
                "max": max_val,
                "device": device_name
            }

        # Fallback to standard get/max
        curr_res = subprocess.run(["brightnessctl", "get"], capture_output=True, text=True, timeout=2.0)
        max_res = subprocess.run(["brightnessctl", "max"], capture_output=True, text=True, timeout=2.0)
        curr = int(curr_res.stdout.strip())
        max_val = int(max_res.stdout.strip())
        pct = round((curr / max_val) * 100) if max_val > 0 else 50
        return {
            "success": True,
            "percent": pct,
            "current": curr,
            "max": max_val,
            "device": "primary"
        }
    except Exception as e:
        return {"success": False, "error": str(e), "percent": 50, "device": "error"}

def set_brightness(percent: int) -> dict:
    """
    Sets display brightness to a specific percentage (1% to 100%).
    Strict argv list, zero shell execution.
    """
    if not shutil.which("brightnessctl"):
        return {"success": False, "error": "brightnessctl utility not installed"}

    clamped = max(1, min(100, int(percent)))
    try:
        res = subprocess.run(
            ["brightnessctl", "set", f"{clamped}%"],
            capture_output=True, text=True, timeout=3.0
        )
        if res.returncode == 0:
            return {
                "success": True,
                "percent": clamped,
                "message": f"Display illumination calibrated to {clamped}%, Sir."
            }
        return {"success": False, "error": res.stderr.strip() or "Permission or hardware error"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def change_brightness(delta: int) -> dict:
    """
    Increases or decreases display brightness by delta percentage.
    """
    if not shutil.which("brightnessctl"):
        return {"success": False, "error": "brightnessctl utility not installed"}

    sign = "+" if delta >= 0 else "-"
    abs_val = abs(int(delta))
    arg = f"{abs_val}%{sign}"
    try:
        res = subprocess.run(
            ["brightnessctl", "set", arg],
            capture_output=True, text=True, timeout=3.0
        )
        if res.returncode == 0:
            curr = get_brightness()
            return {
                "success": True,
                "percent": curr["percent"],
                "message": f"Display illumination shifted by {sign}{abs_val}%. Currently at {curr['percent']}%, Sir."
            }
        return {"success": False, "error": res.stderr.strip() or "Failed to shift brightness"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def lock_session() -> dict:
    """
    Secures active desktop workstation via loginctl with DBus ScreenSaver fallbacks.
    Strict argv list without shell execution.
    """
    # 1. Primary: loginctl lock-session
    if shutil.which("loginctl"):
        try:
            res = subprocess.run(["loginctl", "lock-session"], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                return {"success": True, "method": "loginctl", "message": "Workstation perimeter secured. Session locked, Sir."}
        except Exception:
            pass

    # 2. Secondary fallback: qdbus
    if shutil.which("qdbus"):
        try:
            res = subprocess.run(["qdbus", "org.freedesktop.ScreenSaver", "/ScreenSaver", "Lock"], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                return {"success": True, "method": "qdbus", "message": "Workstation perimeter secured via ScreenSaver DBus, Sir."}
        except Exception:
            pass

    # 3. Tertiary fallback: dbus-send
    if shutil.which("dbus-send"):
        try:
            res = subprocess.run([
                "dbus-send", "--type=method_call",
                "--dest=org.freedesktop.ScreenSaver",
                "/ScreenSaver", "org.freedesktop.ScreenSaver.Lock"
            ], capture_output=True, text=True, timeout=3.0)
            if res.returncode == 0:
                return {"success": True, "method": "dbus-send", "message": "Workstation perimeter secured via dbus-send, Sir."}
        except Exception:
            pass

    return {"success": False, "error": "All session locking mechanisms failed or unavailable on host"}

def get_power_status() -> dict:
    """
    Returns battery charge, power source, and estimated runtime.
    """
    bat = psutil.sensors_battery()
    if bat is None:
        return {
            "success": True,
            "has_battery": False,
            "status_text": "Host machine operating on primary AC utility power, Sir."
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
