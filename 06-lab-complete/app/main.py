import json
import logging
import signal
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import add_cost, check_budget
from app.rate_limiter import check_rate_limit


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        return json.dumps(payload, ensure_ascii=True)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger("agent")
logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
logger.handlers = [handler]
logger.propagate = False

START_TIME = time.time()
redis_client = redis.from_url(settings.redis_url, decode_responses=True)
APP_STATE = {"shutting_down": False}


def mock_llm_response(question: str, history: list[dict[str, str]]) -> str:
    return f"Mock response to '{question}'. Previous turns: {len(history)}"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    model: str
    history_turns: int


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(json.dumps({"event": "startup"}))
    yield
    logger.info(json.dumps({"event": "shutdown"}))


app = FastAPI(title="Production Agent", lifespan=lifespan)


@app.middleware("http")
async def access_log(request: Request, call_next):
    started = time.time()
    if APP_STATE["shutting_down"] and request.url.path not in {"/health", "/ready"}:
        raise HTTPException(status_code=503, detail="Server shutting down")
    response = await call_next(request)
    duration_ms = round((time.time() - started) * 1000, 2)
    logger.info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
    )
    return response


def _sigterm_handler(signum, _frame):
    APP_STATE["shutting_down"] = True
    logger.info(json.dumps({"event": "SIGTERM", "signal": signum}))


signal.signal(signal.SIGTERM, _sigterm_handler)


@app.get("/health")
def health():
    return {"status": "ok", "uptime_seconds": round(time.time() - START_TIME, 2)}


@app.get("/ready")
def ready():
    try:
        if APP_STATE["shutting_down"]:
            raise HTTPException(status_code=503, detail="Shutting down")
        redis_client.ping()
        return {"status": "ready"}
    except redis.RedisError as exc:
        logger.error(json.dumps({"event": "ready_failed", "error": str(exc)}))
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc


@app.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    user_id: str = Depends(verify_api_key),
    _rate_limit: None = Depends(check_rate_limit),
    _budget: None = Depends(check_budget),
):
    history_key = f"conversation:{user_id}"
    raw_history = redis_client.lrange(history_key, 0, settings.conversation_max_turns - 1)
    history = [json.loads(item) for item in raw_history]

    answer = mock_llm_response(payload.question, history)
    new_turn = {"question": payload.question, "answer": answer}

    pipe = redis_client.pipeline()
    pipe.lpush(history_key, json.dumps(new_turn))
    pipe.ltrim(history_key, 0, settings.conversation_max_turns - 1)
    pipe.expire(history_key, 60 * 60 * 24 * 30)
    pipe.execute()

    add_cost(user_id, settings.estimated_cost_per_request_usd)
    return AskResponse(
        user_id=user_id,
        question=payload.question,
        answer=answer,
        model=settings.llm_model,
        history_turns=len(history) + 1,
    )
