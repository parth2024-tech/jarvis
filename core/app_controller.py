import subprocess
import shlex
import os
from sandbox import secure_execute

KNOWN_APPS = {
    "terminal": ["kitty"],
    "editor": ["code"],
    "code": ["code"],
    "files": ["xdg-open", "/home/thor"],
    "browser": ["xdg-open", "https://google.com"],
    "hud": ["xdg-open", "/home/thor/Desktop/JARVIS/ui/hud.html"]
}

def send_notification(title: str, message: str, urgency: str = "normal") -> dict:
    """
    Dispatches a native desktop notification via notify-send.
    """
    valid_urgencies = {"low", "normal", "critical"}
    urg = urgency if urgency in valid_urgencies else "normal"
    clean_title = f"J.A.R.V.I.S. // {title}"
    
    try:
        subprocess.run(
            ["notify-send", clean_title, message, "-u", urg, "-a", "JARVIS"],
            check=False, timeout=3
        )
        return {"success": True, "message": f"Notification delivered: '{clean_title}'"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def launch_app(app_name: str, argument: str = None) -> dict:
    """
    Launches an application or opens a resource in the desktop environment.
    """
    key = app_name.lower().strip()
    if key in KNOWN_APPS:
        cmd_args = list(KNOWN_APPS[key])
        if argument:
            cmd_args.append(argument)
    elif key.startswith("http://") or key.startswith("https://"):
        cmd_args = ["xdg-open", key]
    elif os.path.exists(key):
        cmd_args = ["xdg-open", key]
    else:
        # Generic launcher
        cmd_args = [key]
        if argument:
            cmd_args.append(argument)

    command_str = " ".join(shlex.quote(a) for a in cmd_args)
    # Check security policy first
    res = secure_execute(command_str)
    if res["success"]:
        return {"success": True, "message": f"Application '{key}' initialized, Sir."}
    return {"success": False, "error": res.get("output", f"Failed to launch '{key}'")}
