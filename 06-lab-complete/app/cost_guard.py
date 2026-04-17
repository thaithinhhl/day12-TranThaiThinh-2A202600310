from datetime import datetime, timezone

import redis
from fastapi import Depends, HTTPException

from app.auth import verify_api_key
from app.config import settings

r = redis.from_url(settings.redis_url, decode_responses=True)


def monthly_key(user_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"cost:{user_id}:{month}"


def check_budget(user_id: str = Depends(verify_api_key)) -> None:
    spent = float(r.get(monthly_key(user_id)) or 0.0)
    if spent >= settings.monthly_budget_usd:
        raise HTTPException(status_code=402, detail="Monthly budget exceeded")


def add_cost(user_id: str, amount_usd: float) -> float:
    key = monthly_key(user_id)
    total = r.incrbyfloat(key, amount_usd)
    r.expire(key, 60 * 60 * 24 * 40)
    return float(total)
