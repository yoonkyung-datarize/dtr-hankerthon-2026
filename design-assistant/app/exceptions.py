from fastapi import Request
from fastapi.responses import JSONResponse


class RateLimitExceededException(Exception):
    def __init__(self, message: str = "요청 한도를 초과했습니다."):
        self.message = message


class ClaudeApiException(Exception):
    def __init__(self, message: str = "AI 서비스 오류가 발생했습니다.", detail: str | None = None):
        self.message = message
        self.detail = detail


async def rate_limit_handler(request: Request, exc: RateLimitExceededException):
    return JSONResponse(
        status_code=429,
        content={"code": "4029", "message": exc.message},
    )


async def claude_api_handler(request: Request, exc: ClaudeApiException):
    return JSONResponse(
        status_code=502,
        content={"code": "5002", "message": exc.message},
    )


async def general_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"code": "5000", "message": "내부 서버 오류가 발생했습니다."},
    )
