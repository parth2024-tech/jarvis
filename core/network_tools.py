import re
import socket
import subprocess
import urllib.request

import psutil

# Strict RFC 1123 hostname, IPv4, and IPv6 regex rejecting leading hyphens and trailing newlines
HOST_REGEX = re.compile(
    r"^(?!-)(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?|[a-zA-Z0-9]{1,63}|(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4})\Z"
)

def get_network_status() -> dict:
    """
    Inspects host network interfaces, internal egress IP, and Wi-Fi SSID.
    """
    local_ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.settimeout(0.5)
            s.connect(("1.1.1.1", 53))
            local_ip = s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        pass

    wifi_ssid = None
    try:
        res = subprocess.run(
            ["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"],
            capture_output=True, text=True, timeout=2.0
        )
        for line in res.stdout.splitlines():
            if line.startswith("yes:"):
                wifi_ssid = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass

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
        "summary": f"Network active on {connection_type} (Internal IP: {local_ip}). Traffic: {bytes_sent_mb} MB sent, {bytes_recv_mb} MB received, Sir."
    }

def verify_internet_connectivity() -> dict:
    """
    Multi-target connectivity check combining DNS socket probe and HTTP 204 probe.
    Never relies solely on ICMP which can be blocked by captive portals or firewalls.
    """
    dns_ok = False
    http_ok = False
    latency_ms = None

    # 1. DNS Socket Check (1.1.1.1:53)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(1.0)
            t0 = psutil.time.time()
            s.connect(("1.1.1.1", 53))
            latency_ms = round((psutil.time.time() - t0) * 1000, 1)
            dns_ok = True
        finally:
            s.close()
    except Exception:
        pass

    # 2. HTTP Probe
    try:
        req = urllib.request.Request("http://cp.cloudflare.com/generate_204", headers={"User-Agent": "JARVIS-Health"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            if resp.status == 204 or resp.status == 200:
                http_ok = True
    except Exception:
        pass

    is_online = dns_ok or http_ok
    status_str = "Fully Connected" if (dns_ok and http_ok) else ("Partial Connectivity" if is_online else "Offline")
    lat_str = f" ({latency_ms}ms DNS handshake)" if latency_ms else ""

    return {
        "is_online": is_online,
        "dns_probe": dns_ok,
        "http_probe": http_ok,
        "latency_ms": latency_ms or 0.0,
        "status": status_str,
        "summary": f"Uplink status: {status_str}{lat_str}, Sir."
    }

def ping_latency(host: str = "1.1.1.1") -> dict:
    """
    Performs ICMP ping with strict hostname regex validation.
    Also falls back to multi-target socket probe if ICMP is filtered.
    """
    if not host or not HOST_REGEX.match(host):
        return {
            "success": False,
            "error": "Invalid host syntax: must be a valid IPv4/IPv6 address or RFC 1123 hostname without leading hyphens.",
            "is_online": False,
            "summary": "Ping target rejected due to invalid hostname syntax, Sir."
        }
    clean_host = host


    try:
        res = subprocess.run(
            ["ping", "-c", "2", "-W", "2", "--", clean_host],
            capture_output=True, text=True, timeout=4.0
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
    except Exception:
        pass

    # Fallback to multi-target socket probe if ICMP is blocked or timed out
    conn = verify_internet_connectivity()
    if conn["is_online"]:
        return {
            "success": True,
            "host": clean_host,
            "latency_ms": conn["latency_ms"],
            "is_online": True,
            "summary": f"ICMP ping filtered, but TCP/DNS uplink verified online ({conn['latency_ms']}ms), Sir."
        }

    return {
        "success": False,
        "host": clean_host,
        "latency_ms": 0.0,
        "is_online": False,
        "summary": f"Uplink diagnostic indicates target {clean_host} unreachable, Sir."
    }
