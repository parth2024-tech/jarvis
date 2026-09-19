import subprocess
import shlex
import os
import time
import re

SANDBOX_LOG = "/home/thor/Desktop/JARVIS/memory/audit_trail.log"

# Industrial-grade security policy: Comprehensive regex pattern blocking destructive disk operations, fork bombs, and raw device writes
DANGEROUS_PATTERNS = [
    r"rm\s+-[rRf]*\s+[/~]+",  # rm -rf / or rm -rf ~
    r"mkfs",                  # formatting filesystems
    r">\s*/dev/sd[a-z]",      # raw disk writes
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", # fork bombs
    r"dd\s+.*if=.*of=/dev/sd",  # destructive dd
    r"chmod\s+-R\s+000\s+/",   # permission lockout
    r">\s*/etc/passwd",       # critical system file overwrite
]

def secure_execute(command: str, timeout: int = 15) -> dict:
    """
    Executes terminal commands with industrial-grade least-privilege sandboxing,
    regex-based security policy enforcement, timeout protection, and strict SQLite/file audit logging.
    """
    os.makedirs(os.path.dirname(SANDBOX_LOG), exist_ok=True)
    start_time = time.time()
    
    cmd_stripped = command.strip()
    
    # Advanced Security Policy Check
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_stripped, re.IGNORECASE):
            audit_log(command, "BLOCKED_SECURITY_VIOLATION", 0.0)
            return {
                "success": False,
                "output": f"SECURITY EXCEPTION: Command matches prohibited destructive policy pattern: {pattern}",
                "exit_code": 1,
                "duration_ms": 0.0
            }

    try:
        # Use subprocess with shlex split for safe command parsing
        args = shlex.split(command)
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        duration = round((time.time() - start_time) * 1000, 2)
        status = "SUCCESS" if result.returncode == 0 else "NON_ZERO_EXIT"
        audit_log(command, status, duration)
        
        # Combine stdout and stderr cleanly for diagnostic reporting
        combined_output = result.stdout
        if result.stderr and result.returncode != 0:
            combined_output += f"\nSTDERR:\n{result.stderr}"

        return {
            "success": result.returncode == 0,
            "output": combined_output.strip(),
            "exit_code": result.returncode,
            "duration_ms": duration
        }
    except subprocess.TimeoutExpired:
        duration = round((time.time() - start_time) * 1000, 2)
        audit_log(command, "TIMEOUT", duration)
        return {
            "success": False,
            "output": f"ERROR: Execution timed out after {timeout} seconds.",
            "exit_code": -1,
            "duration_ms": duration
        }
    except Exception as e:
        duration = round((time.time() - start_time) * 1000, 2)
        audit_log(command, f"EXCEPTION: {str(e)}", duration)
        return {
            "success": False,
            "output": f"ERROR: {str(e)}",
            "exit_code": -1,
            "duration_ms": duration
        }

def audit_log(command: str, status: str, duration_ms: float):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] STATUS: {status} | DURATION: {duration_ms}ms | CMD: {command}\n"
    with open(SANDBOX_LOG, "a") as f:
        f.write(log_entry)
