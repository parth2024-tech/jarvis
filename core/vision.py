import os
import time
import subprocess
from PIL import Image

JARVIS_DIR = "/home/thor/Desktop/JARVIS"
SCREENSHOT_PATH = os.path.join(JARVIS_DIR, "memory", "last_vision_capture.png")

def capture_screen_state() -> dict:
    """
    Captures current desktop screen state for J.A.R.V.I.S. multimodal analysis
    using native KDE spectacle, grim, or ImageMagick without shell=True.
    """
    os.makedirs(os.path.dirname(SCREENSHOT_PATH), exist_ok=True)
    start_time = time.time()

    # Prioritized native screen capture commands for Linux desktop
    commands = [
        ["spectacle", "-b", "-n", "-o", SCREENSHOT_PATH],
        ["spectacle", "-b", "-f", "-o", SCREENSHOT_PATH],
        ["grim", SCREENSHOT_PATH],
        ["import", "-window", "root", SCREENSHOT_PATH],
        ["scrot", "-z", SCREENSHOT_PATH]
    ]

    success = False
    last_error = ""

    for cmd in commands:
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            # Give filesystem a moment if needed
            if os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH) > 0:
                success = True
                break
            elif res.returncode == 0:
                time.sleep(0.5)
                if os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH) > 0:
                    success = True
                    break
            last_error = res.stderr.strip() or f"Exit {res.returncode}"
        except FileNotFoundError:
            continue
        except Exception as e:
            last_error = str(e)

    duration = round((time.time() - start_time) * 1000, 2)

    if not success:
        return {
            "success": False,
            "error": f"Screen capture failed: {last_error or 'No supported capture utility available'}",
            "path": None,
            "duration_ms": duration
        }

    # Inspect image dimensions with PIL
    width, height = 0, 0
    try:
        with Image.open(SCREENSHOT_PATH) as img:
            width, height = img.size
    except Exception:
        pass

    return {
        "success": True,
        "path": SCREENSHOT_PATH,
        "width": width,
        "height": height,
        "size_kb": round(os.path.getsize(SCREENSHOT_PATH) / 1024, 1),
        "duration_ms": duration,
        "summary": f"Desktop screen ({width}x{height} px) captured to memory buffer."
    }
