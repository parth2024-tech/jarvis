import os
import secrets
import hmac
import json
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

TOKEN_PATH = os.path.expanduser("~/.jarvis_auth_token")

def get_or_create_auth_token() -> str:
    """
    Retrieves the persistent J.A.R.V.I.S. security bearer token, or generates
    a cryptographically secure 256-bit token with restrictive permissions (0600).
    """
    env_token = os.environ.get("JARVIS_AUTH_TOKEN")
    if env_token:
        return env_token.strip()

    if os.path.exists(TOKEN_PATH):
        try:
            with open(TOKEN_PATH, "r") as f:
                token = f.read().strip()
                if token:
                    return token
        except Exception:
            pass

    # Generate new cryptographically secure token
    new_token = secrets.token_urlsafe(32)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = 0o600
        fd = os.open(TOKEN_PATH, flags, mode)
        with os.fdopen(fd, "w") as f:
            f.write(new_token)
    except Exception as e:
        print(f"[SECURITY WARNING] Failed to persist auth token: {e}")
    return new_token

AUTH_TOKEN = get_or_create_auth_token()

def verify_token(provided_token: str) -> bool:
    """
    Performs constant-time comparison to prevent timing attacks.
    """
    if not provided_token:
        return False
    tok = provided_token.strip()
    if tok.lower().startswith("bearer "):
        tok = tok[7:].strip()
    return hmac.compare_digest(tok, AUTH_TOKEN)

ALLOWED_HOSTS = {
    "127.0.0.1:8090",
    "localhost:8090",
    "127.0.0.1",
    "localhost",
    "testserver"
}

ALLOWED_ORIGINS = {
    "http://127.0.0.1:8090",
    "http://localhost:8090",
    "https://127.0.0.1:8090",
    "https://localhost:8090",
    "null"  # Browsers send 'null' for file:// URLs
}

class HostValidationMiddleware(BaseHTTPMiddleware):
    """
    Guards against DNS Rebinding attacks by strictly rejecting requests
    with unexpected Host headers.
    """
    def __init__(self, app, allowed_port: int = 8090):
        super().__init__(app)
        self.allowed_port = allowed_port
        self.allowed_hosts = set(ALLOWED_HOSTS)
        if allowed_port != 8090:
            self.allowed_hosts.add(f"127.0.0.1:{allowed_port}")
            self.allowed_hosts.add(f"localhost:{allowed_port}")

    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "").split(",")[0].strip()
        if host and host not in self.allowed_hosts:
            return Response(
                status_code=403,
                content=json.dumps({
                    "success": False,
                    "error": {
                        "code": "SECURITY_HOST_VIOLATION",
                        "message": f"Forbidden: Host '{host}' rejected to prevent DNS rebinding."
                    }
                }),
                media_type="application/json"
            )
        return await call_next(request)

class OriginValidationMiddleware(BaseHTTPMiddleware):
    """
    Blocks cross-origin requests from external web pages.
    Permits local file:// origin ('null') and local loopback origins.
    """
    def __init__(self, app, allowed_port: int = 8090):
        super().__init__(app)
        self.allowed_origins = set(ALLOWED_ORIGINS)
        if allowed_port != 8090:
            self.allowed_origins.add(f"http://127.0.0.1:{allowed_port}")
            self.allowed_origins.add(f"http://localhost:{allowed_port}")

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        if origin and origin not in self.allowed_origins:
            return Response(
                status_code=403,
                content=json.dumps({
                    "success": False,
                    "error": {
                        "code": "SECURITY_ORIGIN_VIOLATION",
                        "message": f"Forbidden: Origin '{origin}' rejected to prevent CSRF and external cross-site access."
                    }
                }),
                media_type="application/json"
            )
        return await call_next(request)

def extract_token(request: Request) -> str:
    """
    Extracts authentication token from Authorization Bearer, X-Jarvis-Token, or query parameter.
    """
    # 1. Bearer Header
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()

    # 2. Custom header
    x_token = request.headers.get("x-jarvis-token")
    if x_token:
        return x_token.strip()

    # 3. Query param (for WebSocket handshake and media streams)
    q_token = request.query_params.get("token")
    if q_token:
        return q_token.strip()

    return ""

async def require_auth(request: Request):
    """
    FastAPI dependency requiring valid Bearer or X-Jarvis-Token.
    """
    token = extract_token(request)
    if not token or not verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTH_REQUIRED",
                "message": "Access denied: Missing or invalid J.A.R.V.I.S. Bearer Token."
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    return True
