import hashlib, hmac, secrets
from datetime import datetime, timezone, timedelta
from fastapi import Header, HTTPException
from .config import get_settings

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def iso(dt: datetime | None = None) -> str:
    return (dt or utcnow()).isoformat()

def random_secret() -> str:
    return secrets.token_urlsafe(32)

def digest(value: str) -> str:
    return hmac.new(get_settings().bridge_secret.get_secret_value().encode(), value.encode(), hashlib.sha256).hexdigest()

def verify_digest(value: str, expected: str) -> bool:
    return hmac.compare_digest(digest(value), expected)

async def require_admin(authorization: str | None = Header(default=None)):
    expected = get_settings().bridge_admin_token.get_secret_value()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required")
    supplied = authorization[7:]
    if expected in ("change-me", "") or not hmac.compare_digest(supplied, expected):
        raise HTTPException(401, "Invalid admin token")

def require_agent_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Agent bearer token required")
    return authorization[7:]

def expires_in(minutes: int) -> str:
    return iso(utcnow() + timedelta(minutes=minutes))
