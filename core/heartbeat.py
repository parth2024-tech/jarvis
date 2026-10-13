import os
import sqlite3
import threading
import time

from system_telemetry import get_system_metrics

JARVIS_DIR = "/home/thor/Desktop/JARVIS"
DB_PATH = os.path.join(JARVIS_DIR, "memory", "jarvis_state.db")

class ProactiveHeartbeat:
    """
    Autonomous background daemon for J.A.R.V.I.S. that inspects real-time
    host hardware telemetry, detects resource anomalies, and records proactive briefings.
    """
    def __init__(self, interval_seconds: int = 30):
        self.interval = interval_seconds
        self.running = False
        self._thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)

    def _loop(self):
        while self.running:
            time.sleep(self.interval)
            self._check_and_log()

    def _check_and_log(self):
        try:
            m = get_system_metrics()
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Record metrics into telemetry table
            ts = time.time()
            cursor.execute(
                "INSERT INTO telemetry (timestamp, metric, value) VALUES (?, ?, ?)",
                (ts, "cpu_percent", str(m["cpu_percent"]))
            )
            cursor.execute(
                "INSERT INTO telemetry (timestamp, metric, value) VALUES (?, ?, ?)",
                (ts, "ram_percent", str(m["ram_percent"]))
            )
            cursor.execute(
                "INSERT INTO telemetry (timestamp, metric, value) VALUES (?, ?, ?)",
                (ts, "reactor_stability", str(m["reactor_stability"]))
            )

            # Anomaly detection gates
            is_anomaly = False
            warning_notes = []

            if m["cpu_percent"] > 90.0:
                is_anomaly = True
                warning_notes.append(f"Elevated CPU load: {m['cpu_percent']}%")
            if m["ram_percent"] > 90.0:
                is_anomaly = True
                warning_notes.append(f"Critical memory pressure: {m['ram_percent']}%")
            if m["temperature_c"] and m["temperature_c"] > 85.0:
                is_anomaly = True
                warning_notes.append(f"High thermal reading: {m['temperature_c']}°C")
            if m["battery"] and m["battery"]["percent"] < 20.0 and not m["battery"]["power_plugged"]:
                is_anomaly = True
                warning_notes.append(f"Auxiliary battery reserve low: {m['battery']['percent']}%")

            if is_anomaly:
                briefing = f"WARNING: Anomaly detected, Sir. {'; '.join(warning_notes)}. Reactor stability at {m['reactor_stability']}%."
                intent = "proactive_alert"
            else:
                briefing = f"Proactive scan: All systems nominal. Reactor stability at {m['reactor_stability']}%. CPU load at {m['cpu_percent']}%, Memory at {m['ram_percent']}%."
                intent = "proactive_briefing"

            cursor.execute(
                "INSERT INTO interactions (timestamp, speaker, message, intent) VALUES (?, ?, ?, ?)",
                (ts, "jarvis_daemon", briefing, intent)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[HEARTBEAT ERROR] {e}")
