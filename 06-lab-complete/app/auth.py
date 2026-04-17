import hmac

from fastapi import Header, HTTPException

from app.config import settings


def verify_api_key(
    x_api_key: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.agent_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_user_id or "anonymous"
