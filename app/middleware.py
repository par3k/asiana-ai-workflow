import logging
import time
import uuid

from fastapi import FastAPI, Request

from app.services.auth import decode_access_token

logger = logging.getLogger("api.access")


def _member_id_from_request(request: Request) -> str:
    # 토큰 값은 기록하지 않고 member_id(sub)만 꺼낸다. 비로그인/잘못된 토큰이면 "-"
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return "-"
    try:
        return str(decode_access_token(auth[7:]).get("sub", "-"))
    except Exception:
        return "-"


def add_access_log_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def access_log(request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        member_id = _member_id_from_request(request)
        client = request.client.host if request.client else "-"
        # 쿼리스트링은 기록, 요청 body는 비밀번호 등이 있을 수 있어 기록하지 않음
        target = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception(
                "[%s] %s %s member=%s client=%s -> 500 (예외 발생, %.0fms)",
                request_id, request.method, target, member_id, client, elapsed,
            )
            raise
        elapsed = (time.perf_counter() - start) * 1000
        level = logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(
            level,
            "[%s] %s %s member=%s client=%s -> %s (%.0fms)",
            request_id, request.method, target, member_id, client, response.status_code, elapsed,
        )
        response.headers["X-Request-ID"] = request_id
        return response
