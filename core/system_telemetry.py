import os
import time

import psutil


def get_system_metrics() -> dict:
    """
    Gathers real-time host operating system telemetry and hardware metrics.
    """
    # CPU
    cpu_pct = psutil.cpu_percent(interval=0.05)
    cpu_count = psutil.cpu_count(logical=True)
    load_avg = os.getloadavg() if hasattr(os, "getloadavg") else (0.5, 0.5, 0.5)

    # Memory
    vmem = psutil.virtual_memory()
    ram_total_gb = round(vmem.total / (1024 ** 3), 2)
    ram_used_gb = round(vmem.used / (1024 ** 3), 2)
    ram_pct = vmem.percent

    # Disk
    disk = psutil.disk_usage("/")
    disk_total_gb = round(disk.total / (1024 ** 3), 2)
    disk_free_gb = round(disk.free / (1024 ** 3), 2)
    disk_pct = disk.percent

    # Battery
    battery_info = None
    try:
        bat = psutil.sensors_battery()
        if bat is not None:
            battery_info = {
                "percent": bat.percent,
                "power_plugged": bat.power_plugged,
                "secsleft": bat.secsleft if bat.secsleft != psutil.POWER_TIME_UNLIMITED else None
            }
    except Exception:
        battery_info = None

    # Temperatures
    temp_c = None
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                if entries:
                    temp_c = round(entries[0].current, 1)
                    break
    except Exception:
        temp_c = None

    # Top processes by memory/cpu
    top_procs = []
    try:
        for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']),
                        key=lambda x: x.info.get('cpu_percent') or 0, reverse=True)[:5]:
            top_procs.append({
                "pid": p.info['pid'],
                "name": p.info['name'],
                "cpu_percent": p.info.get('cpu_percent', 0.0),
                "memory_percent": round(p.info.get('memory_percent', 0.0), 1)
            })
    except Exception:
        pass

    # Reactor stability derived index (Iron Man thematic indicator)
    base_stability = 100.0 - (cpu_pct * 0.15 + (ram_pct - 20) * 0.1 if ram_pct > 20 else 0)
    reactor_stability = round(max(50.0, min(99.9, base_stability)), 1)

    return {
        "timestamp": time.time(),
        "reactor_stability": reactor_stability,
        "cpu_percent": cpu_pct,
        "cpu_count": cpu_count,
        "load_avg_1m": round(load_avg[0], 2),
        "ram_total_gb": ram_total_gb,
        "ram_used_gb": ram_used_gb,
        "ram_percent": ram_pct,
        "disk_total_gb": disk_total_gb,
        "disk_free_gb": disk_free_gb,
        "disk_percent": disk_pct,
        "battery": battery_info,
        "temperature_c": temp_c,
        "top_processes": top_procs
    }

def get_telemetry_summary() -> str:
    """
    Returns an authentic J.A.R.V.I.S.-styled diagnostic summary of system health.
    """
    m = get_system_metrics()
    parts = [
        f"Reactor stability is at {m['reactor_stability']}%.",
        f"CPU load is {m['cpu_percent']}% across {m['cpu_count']} virtual cores (1m load average: {m['load_avg_1m']}).",
        f"Memory utilization stands at {m['ram_percent']}% ({m['ram_used_gb']} GB of {m['ram_total_gb']} GB committed).",
        f"Primary storage reports {m['disk_free_gb']} GB free of {m['disk_total_gb']} GB ({m['disk_percent']}% utilized)."
    ]
    if m['temperature_c'] is not None:
        parts.append(f"Thermal sensors register {m['temperature_c']}°C.")
    if m['battery'] is not None:
        status = "charging" if m['battery']['power_plugged'] else "on battery reserve"
        parts.append(f"Auxiliary battery is at {m['battery']['percent']}% ({status}).")
    return " ".join(parts)
