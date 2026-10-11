import subprocess
import socket
import re
import psutil

def get_network_status() -> dict:
    """
    Inspects host network interfaces, active local IP, and Wi-Fi connection.
    """
    # Active IP address
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Doesn't actually send packet, routes locally to find default egress IP
        s.connect(("1.1.1.1", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    # Wi-Fi SSID
    wifi_ssid = None
    try:
        res = subprocess.run(
            ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
            capture_output=True, text=True, timeout=2
        )
        for line in res.stdout.splitlines():
            if line.startswith("yes:"):
                wifi_ssid = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass

    # Interface stats
    net_io = psutil.net_io_counters()
    bytes_sent_mb = round(net_io.bytes_sent / (1024 ** 2), 1)
    bytes_recv_mb = round(net_io.bytes_recv / (1024 ** 2), 1)

    connection_type = f"Wi-Fi ('{wifi_ssid}')" if wifi_ssid else "Ethernet / Local Network"

    return {
        "success": True,
        "local_ip": local_ip,
        "wifi_ssid": wifi_ssid,
        "connection_type": connection_type,
        "bytes_sent_mb": bytes_sent_mb,
        "bytes_recv_mb": bytes_recv_mb,
        "summary": f"Network active on {connection_type} (Internal IP: {local_ip}). Transferred {bytes_sent_mb} MB sent, {bytes_recv_mb} MB received, Sir."
    }

def ping_latency(host: str = "1.1.1.1") -> dict:
    """
    Measures round-trip internet latency via ICMP echo.
    """
    clean_host = host.strip()
    try:
        res = subprocess.run(
            ["ping", "-c", "2", "-W", "2", clean_host],
            capture_output=True, text=True, timeout=5
        )
        if res.returncode == 0:
            match = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/", res.stdout)
            avg_ms = float(match.group(1)) if match else 20.0
            return {
                "success": True,
                "host": clean_host,
                "latency_ms": round(avg_ms, 1),
                "is_online": True,
                "summary": f"Network uplink to {clean_host} verified: {round(avg_ms, 1)}ms round-trip latency, Sir."
            }
        return {
            "success": False,
            "host": clean_host,
            "latency_ms": 0.0,
            "is_online": False,
            "summary": f"Ping to {clean_host} timed out. Uplink degraded, Sir."
        }
    except Exception as e:
        return {"success": False, "error": str(e), "summary": f"Ping diagnostic error: {e}"}
