import os
import time
import sqlite3
import threading
import uuid
import subprocess
from app_controller import send_notification

JARVIS_DIR = "/home/thor/Desktop/JARVIS"
DB_PATH = os.path.join(JARVIS_DIR, "memory", "jarvis_state.db")

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn

def init_productivity_schema():
    conn = get_db()
    cursor = conn.cursor()
    # Todos Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'normal',
            created_at REAL NOT NULL,
            completed_at REAL
        )
    """)
    # Persistent Timers Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS timers (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            duration_seconds INTEGER NOT NULL,
            expires_at REAL NOT NULL,
            status TEXT DEFAULT 'active',
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_productivity_schema()

# ========================================================
# 1. Persistent Timers Engine with Reboot Rehydration
# ========================================================
ACTIVE_TIMERS = {}
_timer_lock = threading.Lock()

def _timer_worker(timer_id: str, delay_seconds: float, label: str):
    time.sleep(max(0.1, delay_seconds))
    with _timer_lock:
        if timer_id not in ACTIVE_TIMERS:
            return  # Cancelled
        del ACTIVE_TIMERS[timer_id]

    # Update database record
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE timers SET status = 'completed' WHERE id = ?", (timer_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

    # Timer Expired Alert
    title = f"TIMER COMPLETE: {label.upper()}"
    msg = f"Your countdown for '{label}' has concluded, Sir."
    send_notification(title, msg, urgency="critical")

    # Local speech alert
    try:
        from voice_engine import play_speech_locally
        play_speech_locally(f"Sir, your timer for {label} is complete.", voice_key="alexa")
    except Exception:
        pass

def set_timer(duration_seconds: int, label: str = "General Directive") -> dict:
    """
    Schedules an autonomous background countdown timer persisted in SQLite.
    Survives server restarts and provides absolute timestamp coordinates.
    """
    sec = max(1, int(duration_seconds))
    timer_id = str(uuid.uuid4())[:8]
    now = time.time()
    expires_at = now + sec

    # Persist to SQLite
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO timers (id, label, duration_seconds, expires_at, status, created_at) VALUES (?, ?, ?, ?, 'active', ?)",
            (timer_id, label, sec, expires_at, now)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        return {"success": False, "error": f"Failed to persist timer: {e}"}

    timer_record = {
        "id": timer_id,
        "label": label,
        "duration_seconds": sec,
        "expires_at": expires_at,
        "created_at": now
    }

    with _timer_lock:
        ACTIVE_TIMERS[timer_id] = timer_record

    t = threading.Thread(target=_timer_worker, args=(timer_id, sec, label), daemon=True)
    t.start()

    if sec >= 60:
        mins = sec // 60
        rem_sec = sec % 60
        dur_str = f"{mins} minute{'s' if mins != 1 else ''}" + (f" {rem_sec}s" if rem_sec else "")
    else:
        dur_str = f"{sec} seconds"

    return {
        "success": True,
        "timer_id": timer_id,
        "label": label,
        "duration_seconds": sec,
        "expires_at": expires_at,
        "message": f"Timer initiated for {dur_str} ('{label}'), Sir."
    }

def get_active_timers() -> list:
    """
    Returns currently running countdown timers with absolute expires_at timestamp
    and remaining seconds.
    """
    now = time.time()
    results = []
    with _timer_lock:
        for tid, tinfo in ACTIVE_TIMERS.items():
            rem = max(0, round(tinfo["expires_at"] - now))
            results.append({
                "id": tid,
                "label": tinfo["label"],
                "duration_seconds": tinfo["duration_seconds"],
                "expires_at": tinfo["expires_at"],
                "remaining_seconds": rem
            })
    results.sort(key=lambda x: x["remaining_seconds"])
    return results

def cancel_timer(timer_id: str) -> dict:
    """
    Safely terminates an active timer in memory and marks it cancelled in SQLite.
    """
    found = False
    with _timer_lock:
        if timer_id in ACTIVE_TIMERS:
            del ACTIVE_TIMERS[timer_id]
            found = True

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE timers SET status = 'cancelled' WHERE id = ?", (timer_id,))
        if cursor.rowcount > 0:
            found = True
        conn.commit()
        conn.close()
    except Exception:
        pass

    if found:
        return {"success": True, "message": f"Timer {timer_id} cancelled, Sir."}
    return {"success": False, "message": "Timer identifier not found, Sir."}

def rehydrate_timers():
    """
    Restores active timers from SQLite after server reboot or crash.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, label, duration_seconds, expires_at FROM timers WHERE status = 'active'")
        rows = cursor.fetchall()
        now = time.time()

        for tid, label, dur, exp in rows:
            if exp > now:
                # Timer still running; resume worker with remaining time
                rem = exp - now
                with _timer_lock:
                    ACTIVE_TIMERS[tid] = {
                        "id": tid,
                        "label": label,
                        "duration_seconds": dur,
                        "expires_at": exp,
                        "created_at": exp - dur
                    }
                t = threading.Thread(target=_timer_worker, args=(tid, rem, label), daemon=True)
                t.start()
            else:
                # Timer expired while system/server was offline
                cursor.execute("UPDATE timers SET status = 'completed' WHERE id = ?", (tid,))
                send_notification(
                    f"EXPIRED COUNTDOWN: {label.upper()}",
                    f"Your scheduled timer for '{label}' concluded while core was offline, Sir.",
                    urgency="normal"
                )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[TIMER REHYDRATION ERROR] {e}")

# Rehydrate timers on import
rehydrate_timers()

# ========================================================
# 2. Mission Objectives Registry (Todos)
# ========================================================
def add_todo(task: str, priority: str = "normal") -> dict:
    clean_task = task.strip()
    if not clean_task:
        return {"success": False, "error": "Empty task description"}

    valid_prios = {"low", "normal", "medium", "high", "critical"}
    prio = priority.lower() if priority.lower() in valid_prios else "normal"

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO todos (task, status, priority, created_at) VALUES (?, 'pending', ?, ?)",
            (clean_task, prio, time.time())
        )
        todo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {
            "success": True,
            "id": todo_id,
            "task": clean_task,
            "priority": prio,
            "message": f"Task #{todo_id} recorded to mission log: '{clean_task}', Sir."
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def list_todos(include_completed: bool = False) -> list:
    try:
        conn = get_db()
        cursor = conn.cursor()
        if include_completed:
            cursor.execute("SELECT id, task, status, priority, created_at, completed_at FROM todos ORDER BY id DESC")
        else:
            cursor.execute("SELECT id, task, status, priority, created_at, completed_at FROM todos WHERE status = 'pending' ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "task": r[1],
                "status": r[2],
                "priority": r[3],
                "created_at": r[4],
                "completed_at": r[5]
            }
            for r in rows
        ]
    except Exception:
        return []

def get_todo(todo_id: int) -> dict:
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, task, status, priority, created_at, completed_at FROM todos WHERE id = ?", (int(todo_id),))
        r = cursor.fetchone()
        conn.close()
        if r:
            return {
                "success": True,
                "todo": {
                    "id": r[0],
                    "task": r[1],
                    "status": r[2],
                    "priority": r[3],
                    "created_at": r[4],
                    "completed_at": r[5]
                }
            }
        return {"success": False, "error": f"Task #{todo_id} not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def update_todo(todo_id: int, task: str = None, priority: str = None, status: str = None) -> dict:
    try:
        conn = get_db()
        cursor = conn.cursor()
        fields = []
        params = []
        if task is not None:
            fields.append("task = ?")
            params.append(task.strip())
        if priority is not None:
            fields.append("priority = ?")
            params.append(priority.lower())
        if status is not None:
            fields.append("status = ?")
            params.append(status.lower())
            if status.lower() == "completed":
                fields.append("completed_at = ?")
                params.append(time.time())

        if not fields:
            conn.close()
            return {"success": False, "error": "No update fields provided"}

        params.append(int(todo_id))
        query = f"UPDATE todos SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, params)
        affected = cursor.rowcount
        conn.commit()
        conn.close()

        if affected > 0:
            return {"success": True, "message": f"Task #{todo_id} updated, Sir."}
        return {"success": False, "error": f"Task #{todo_id} not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def complete_todo(todo_id: int) -> dict:
    return update_todo(todo_id, status="completed")

def delete_todo(todo_id: int) -> dict:
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM todos WHERE id = ?", (int(todo_id),))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        if affected > 0:
            return {"success": True, "message": f"Task #{todo_id} excised from registry, Sir."}
        return {"success": False, "error": f"Task #{todo_id} not found"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def clear_completed_todos() -> dict:
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM todos WHERE status = 'completed'")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Purged {deleted} completed tasks from registry, Sir."}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ========================================================
# 3. Wayland Clipboard Bridge (Safe Argv & Stdin Pipe)
# ========================================================
def get_clipboard_text() -> dict:
    """
    Retrieves current text copied on Wayland system clipboard.
    Safe subprocess with explicit argv list and strict timeout.
    """
    try:
        res = subprocess.run(
            ["wl-paste", "--no-newline"],
            capture_output=True,
            text=True,
            timeout=2.0
        )
        text = res.stdout.strip()
        return {
            "success": True,
            "text": text,
            "char_count": len(text)
        }
    except FileNotFoundError:
        return {"success": False, "error": "wl-paste not found on host", "text": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "text": ""}

def set_clipboard_text(text: str) -> dict:
    """
    Injects text into host Wayland clipboard via safe stdin pipe.
    Zero shell execution.
    """
    try:
        p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE, text=True)
        p.communicate(input=text, timeout=2.0)
        return {
            "success": True,
            "message": f"Buffered {len(text)} characters to system clipboard, Sir."
        }
    except FileNotFoundError:
        return {"success": False, "error": "wl-copy not found on host"}
    except Exception as e:
        return {"success": False, "error": str(e)}
