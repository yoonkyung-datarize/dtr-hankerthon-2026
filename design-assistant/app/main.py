from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import DesignRequest, ApiResponse
from app.claude_client import generate_css
from app.rate_limiter import check_and_increment
from app.exceptions import (
    RateLimitExceededException,
    ClaudeApiException,
    rate_limit_handler,
    claude_api_handler,
    general_handler,
)

app = FastAPI(
    title="Design Assistant API",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(RateLimitExceededException, rate_limit_handler)
app.add_exception_handler(ClaudeApiException, claude_api_handler)
app.add_exception_handler(Exception, general_handler)


@app.post("/api/v1/design/generate", response_model=ApiResponse)
async def generate(request: DesignRequest):
    await check_and_increment(request.site_id)
    result = await generate_css(request.site_id, request.prompt)
    return ApiResponse(data=result)

@app.get("/")
async def root():
  return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "ok"}
