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
            if os.path.exists(SCREENSHOT_PATH) and os.path.getsize(SCREENSHOT_PATH) > 0:
                success = True
                break
            elif res.returncode == 0:
                time.sleep(0.4)
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

def read_screen_text() -> dict:
    """
    Captures desktop screenshot and extracts all visible text using Tesseract OCR.
    """
    cap = capture_screen_state()
    if not cap["success"]:
        return {"success": False, "error": cap.get("error", "Failed to capture screen"), "text": ""}

    start_time = time.time()
    try:
        res = subprocess.run(
            ["tesseract", SCREENSHOT_PATH, "stdout", "--psm", "6"],
            capture_output=True,
            text=True,
            timeout=10
        )
        duration = round((time.time() - start_time) * 1000, 2)
        extracted = res.stdout.strip()
        return {
            "success": True,
            "text": extracted,
            "char_count": len(extracted),
            "ocr_duration_ms": duration,
            "path": SCREENSHOT_PATH
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"OCR processing failed: {str(e)}",
            "text": ""
        }

def summarize_screen(question: str = None) -> dict:
    """
    Performs OCR on current screen and uses local LLM to answer questions or summarize what is visible.
    """
    import requests
    ocr_res = read_screen_text()
    if not ocr_res["success"] or not ocr_res["text"]:
        return {
            "success": False,
            "response": "Optical sensors could not identify legible text on the active display, Sir.",
            "ocr_text": ""
        }

    text_sample = ocr_res["text"][:2000]
    prompt_q = question if question else "Summarize the primary content or activity visible on this screen in 1 or 2 concise sentences."

    prompt = f"""You are J.A.R.V.I.S., Tony Stark's AI operating assistant.
Here is the raw text extracted via optical character recognition (OCR) from the user's active computer screen:
---
{text_sample}
---

USER DIRECTIVE: {prompt_q}

Respond concisely with refined British diction as J.A.R.V.I.S., addressing the user as Sir:"""

    try:
        res = requests.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": "llama3.2:latest",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.5, "num_predict": 90}
            },
            timeout=12
        )
        if res.status_code == 200:
            import re
            cleaned = re.sub(r"<think>[\s\S]*?<\/think>", "", res.json().get("response", "")).strip()
            return {
                "success": True,
                "response": cleaned,
                "ocr_text": text_sample[:300]
            }
    except Exception:
        pass

    # Graceful heuristic fallback if LLM is busy
    first_lines = " ".join(text_sample.split("\n")[:3])
    return {
        "success": True,
        "response": f"Visual sensors detect active desktop text: '{first_lines[:120]}...', Sir.",
        "ocr_text": text_sample[:300]
    }
