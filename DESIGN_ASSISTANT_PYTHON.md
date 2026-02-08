# AI 디자인 어시스턴트 - Python FastAPI 구현 지시서

## 프로젝트 개요

위젯 디자인 커스터마이징을 위한 백엔드 API를 Python + FastAPI로 빠르게 구현한다.
사용자가 자연어와 참조 이미지로 디자인 요청을 보내면, Claude API를 호출하여 CSS를 생성하고 응답한다.

---

## 기술 스택

- Python 3.12+
- FastAPI + Uvicorn
- anthropic (공식 Python SDK)
- Redis (rate limiting)
- Pydantic v2 (request/response 모델)

---

## 프로젝트 구조

```
design-assistant/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 진입점
│   ├── config.py               # 환경 변수 설정
│   ├── models.py               # Request/Response 모델
│   ├── prompt.py               # 시스템 프롬프트 & 유저 프롬프트 빌더
│   ├── claude_client.py        # Claude API 호출
│   ├── rate_limiter.py         # Redis 기반 rate limit
│   └── exceptions.py           # 커스텀 예외 & 핸들러
├── requirements.txt
├── Dockerfile
├── .env.example
└── README.md
```

---

## 의존성 (requirements.txt)

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
anthropic==0.52.0
redis==5.3.0
pydantic==2.11.3
pydantic-settings==2.9.1
python-dotenv==1.1.0
```

---

## 환경 변수 (.env.example)

```env
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
ANTHROPIC_MAX_TOKENS=4096
ANTHROPIC_TIMEOUT_SECONDS=60

REDIS_URL=redis://localhost:6379/0

MAX_REQUESTS_PER_SITE=10
RATE_LIMIT_TTL_HOURS=24

# CORS (쉼표 구분)
ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.com
```

---

## 구현할 파일 목록 및 상세 요구사항

### 1. `app/config.py` - 설정

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-5-20250929"
    anthropic_max_tokens: int = 4096
    anthropic_timeout_seconds: int = 60

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Rate Limit
    max_requests_per_site: int = 10
    rate_limit_ttl_hours: int = 24

    # CORS
    allowed_origins: str = "http://localhost:3000"

    model_config = {"env_file": ".env"}


settings = Settings()
```

---

### 2. `app/models.py` - Request/Response 모델

```python
from pydantic import BaseModel
from typing import Optional, Any


class DesignRequest(BaseModel):
    site_id: str
    prompt: str


class DesignGenerateData(BaseModel):
    css: str
    explanation: Optional[str] = None


class ApiResponse(BaseModel):
    code: str = "0000"
    message: str = "Success"
    data: Optional[Any] = None
```

---

### 3. `app/exceptions.py` - 예외 처리

```python
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
```

---

### 4. `app/prompt.py` - 프롬프트 빌더

```python
SYSTEM_PROMPT = """한국어로 응답. 존댓말 사용. 불필요한 설명 금지.

## 입력 형식
```
현재 CSS:
(기존 적용된 CSS 또는 없음)

이전 요청:
1. 첫 번째 요청
2. 두 번째 요청
(또는 없음)

요청: 사용자 요청
```

## 출력 형식
- CSS만 출력 (마크다운 코드블록 없이 일반 CSS 텍스트로)
- 현재 CSS + 새 요청 병합한 전체 CSS 출력
- 모호한 요청 시: 한 문장으로 질문

## 클래스 매핑

| 용어 | 클래스 |
|-----|--------|
| 위젯 전체 | .dtr-widget-main |
| 타이틀 | .dtr-widget-title |
| 캐러셀 | .dtr-widget-carousel |
| 상품 간격 | .dtr-widget-slide |
| 이전/다음 버튼 | .dtr-widget-prev / .dtr-widget-next |
| 상품 카드 | .dtr-widget-item |
| 상품 이미지 | .dtr-widget-item-image |
| 상품 정보 영역 | .dtr-widget-item-container |
| 상품명 | .dtr-widget-item-name |
| 가격 영역 | .dtr-widget-item-price-container |
| 정가 | .dtr-widget-item-original-price |
| 할인율 | .dtr-widget-item-discount-rate |
| 할인가 영역 | .dtr-widget-item-selling-price-container |
| 판매가 | .dtr-widget-item-selling-price |

## 기본 스타일 (globalStyle)

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}

button {
  background: inherit;
  border: none;
  box-shadow: none;
  border-radius: 0;
  padding: 0;
  cursor: pointer;
}

.dtr-widget-carousel {
  overflow: hidden;
}

.dtr-widget-slide {
  display: flex;
  flex-shrink: 0;
  padding-right: 8px;
}

.dtr-widget-prev,
.dtr-widget-next {
  position: absolute;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 24px;
  height: 24px;
  border-radius: 999px;
  top: 50%;
  transform: translateY(-50%);
  background-color: rgba(255, 255, 255, 0.5);
  z-index: 10;
}

.dtr-widget-prev {
  left: -12px;
}

.dtr-widget-next {
  right: -12px;
}

## 기본 스타일 (컴포넌트)

.dtr-widget-title {
  font-weight: 600;
}

.dtr-widget-item {
  display: flex;
  flex-direction: column;
  width: 100%;
  cursor: pointer;
}

.dtr-widget-item-image {
  width: 100%;
  object-fit: cover;
}

.dtr-widget-item-container {
  display: flex;
  flex-direction: column;
  padding: 10px 0;
  gap: 8px;
}

.dtr-widget-item-name {
  font-weight: 400;
  text-align: start;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  display: -webkit-box;
  overflow: hidden;
}

.dtr-widget-item-price-container {
  text-align: start;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dtr-widget-item-original-price {
  text-decoration: line-through;
  color: #868e96;
}

.dtr-widget-item-discount-rate {
  font-weight: 700;
}

.dtr-widget-item-selling-price-container {
  display: flex;
  align-items: center;
  gap: 4px;
}

.dtr-widget-item-selling-price {
  font-weight: 600;
}

## 폰트 변경 시 주의
기본 폰트가 * 선택자로 적용되어 있으므로, 폰트 변경 시 `.dtr-widget-main *` 사용

## 레이아웃 설명

위젯 전체 구조:
┌─────────────────────────────────────────┐
│ [타이틀] 중앙/좌측/우측 정렬 가능        │
│                                         │
│ [◀] [상품1] [상품2] [상품3] [상품4] [▶] │
│      가로 슬라이드 (캐러셀)              │
└─────────────────────────────────────────┘

상품 카드 구조 (세로 배치):
┌──────────────┐
│   [이미지]    │ ← 상단
├──────────────┤
│   상품명      │ ← 최대 2줄
│   ₩15,000    │ ← 정가 (취소선, 회색)
│   20% ₩12,000│ ← 할인율 + 판매가 (가로 배치)
└──────────────┘

가격 배치:
- 정가: 단독 줄
- 할인율 + 판매가: 같은 줄, 할인율이 왼쪽

## DOM 구조
```
.dtr-widget-main
├── .dtr-widget-title
└── .dtr-widget-carousel
    ├── .dtr-widget-track > .dtr-widget-list > .dtr-widget-slide
    │   └── .dtr-widget-item
    │       ├── .dtr-widget-item-image
    │       └── .dtr-widget-item-container
    │           ├── .dtr-widget-item-name
    │           └── .dtr-widget-item-price-container
    │               ├── .dtr-widget-item-original-price
    │               └── .dtr-widget-item-selling-price-container
    │                   ├── .dtr-widget-item-discount-rate
    │                   └── .dtr-widget-item-selling-price
    ├── .dtr-widget-prev
    └── .dtr-widget-next
```

## 규칙
1. 요청한 스타일만 수정
2. dtr-widget-* 클래스만 사용
3. ID 셀렉터, splide__* 클래스 사용 금지
4. 미디어 쿼리 사용 금지
5. 폰트 요청 시 웹 폰트 @import 포함

## 미지원 요소 (이미지 참고 시 무시)
리뷰, 별점, 랭킹 번호, 배지(BEST/NEW), 브랜드명, 배송정보

## 예시

예시 1 - 일반 요청:
입력:
현재 CSS:
.dtr-widget-main * { font-family: 'Noto Sans'; }

이전 요청:
1. 폰트 Noto Sans로 변경 (PC/모바일 둘 다)

요청: 타이틀 굵게, PC만

출력:
.dtr-widget-main * { font-family: 'Noto Sans'; }
.dtr-widget-title { font-weight: 700; }

예시 2 - 이전 요청 취소:
입력:
현재 CSS:
.dtr-widget-main * { font-family: 'Noto Sans'; }
.dtr-widget-title { font-weight: 700; }

이전 요청:
1. 폰트 Noto Sans로 변경
2. 타이틀 굵게

요청: 폰트 변경한 거 취소해주세요

출력:
.dtr-widget-title { font-weight: 700; }
"""


def build_user_prompt(prompt: str) -> str:
    return prompt
```

---

### 5. `app/rate_limiter.py` - Redis Rate Limit

```python
import redis.asyncio as aioredis
from app.config import settings
from app.exceptions import RateLimitExceededException

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None


async def check_and_increment(site_id: str):
    r = await get_redis()
    key = f"design:rate:{site_id}"

    count = await r.incr(key)

    if count == 1:
        await r.expire(key, settings.rate_limit_ttl_hours * 3600)

    if count > settings.max_requests_per_site:
        raise RateLimitExceededException(
            f"사이트 {site_id} 의 일일 요청 한도({settings.max_requests_per_site}회)를 초과했습니다."
        )
```

---

### 6. `app/claude_client.py` - Claude API 호출

```python
import re
import asyncio
import anthropic
from app.config import settings
from app.exceptions import ClaudeApiException
from app.models import DesignGenerateData
from app.prompt import SYSTEM_PROMPT, build_user_prompt

DATA_URL_PATTERN = re.compile(r"data:image/([\w+]+);base64,([A-Za-z0-9+/=]+)")

_client: anthropic.AsyncAnthropic | None = None
_semaphore = asyncio.Semaphore(5)


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=settings.anthropic_timeout_seconds,
        )
    return _client


def extract_image_from_prompt(prompt: str) -> tuple[str, str | None, str | None]:
    """prompt에서 data URL 이미지를 추출한다."""
    match = DATA_URL_PATTERN.search(prompt)
    if match:
        mime_type = f"image/{match.group(1)}"
        base64_data = match.group(2)
        text_only = prompt.replace(match.group(0), "").strip()
        return text_only, base64_data, mime_type
    return prompt, None, None


def strip_code_fences(text: str) -> str:
    """마크다운 코드블록 제거"""
    text = re.sub(r"^```(?:css)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


async def generate_css(site_id: str, raw_prompt: str) -> DesignGenerateData:
    text_prompt, image_base64, image_mime = extract_image_from_prompt(raw_prompt)
    user_prompt = build_user_prompt(text_prompt)

    content: list = []
    if image_base64 and image_mime:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_mime,
                "data": image_base64,
            },
        })
    content.append({"type": "text", "text": user_prompt})

    async with _semaphore:
        response = await _call_with_retry(content)

    css = strip_code_fences(response)
    return DesignGenerateData(css=css)


async def _call_with_retry(content: list, max_retries: int = 2) -> str:
    client = get_client()
    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            message = await client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.anthropic_max_tokens,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
            )
            return "".join(
                block.text for block in message.content if block.type == "text"
            )
        except anthropic.RateLimitError as e:
            last_exc = e
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
            continue
        except Exception as e:
            raise ClaudeApiException("Claude API 호출 실패", str(e))

    raise ClaudeApiException("Claude API 재시도 횟수 초과", str(last_exc))
```

---

### 7. `app/main.py` - FastAPI 앱

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import DesignRequest, ApiResponse, DesignGenerateData
from app.claude_client import generate_css
from app.rate_limiter import check_and_increment, close_redis
from app.exceptions import (
    RateLimitExceededException,
    ClaudeApiException,
    rate_limit_handler,
    claude_api_handler,
    general_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="Design Assistant API",
    version="1.0.0",
    lifespan=lifespan,
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


@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## 로컬 실행

```bash
# 1. 프로젝트 생성
mkdir design-assistant && cd design-assistant
mkdir app && touch app/__init__.py

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY 설정

# 4. Redis 실행 (Docker)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 5. 서버 실행
uvicorn app.main:app --reload --port 8000
```

---

## Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## API 명세

Kotlin 버전과 동일한 인터페이스를 유지한다.

### POST /api/v1/design/generate

**Request (텍스트만):**
```json
{
  "site_id": "site_123",
  "prompt": "버튼 색상을 파란색으로 변경해주세요"
}
```

**Request (이미지 포함):**
```json
{
  "site_id": "site_123",
  "prompt": "이 디자인으로 CSS 만들어줘 data:image/png;base64,iVBORw0KGgo..."
}
```

**Response (Success):**
```json
{
  "code": "0000",
  "message": "Success",
  "data": {
    "css": ".dtr-widget-button { color: blue; }",
    "explanation": null
  }
}
```

**Response (Rate Limit 초과):**
```json
{
  "code": "4029",
  "message": "사이트 site_123 의 일일 요청 한도(10회)를 초과했습니다."
}
```

**Response (AI 서비스 오류):**
```json
{
  "code": "5002",
  "message": "AI 서비스 오류가 발생했습니다."
}
```

### GET /health

헬스체크 엔드포인트.

---

## 구현 순서

| 단계 | 파일 | 작업 내용 |
|----|------|---------|
| 1 | requirements.txt, .env | 의존성 & 환경 변수 설정 |
| 2 | app/config.py | Settings 클래스 |
| 3 | app/models.py | Request/Response 모델 |
| 4 | app/exceptions.py | 예외 클래스 & 핸들러 |
| 5 | app/prompt.py | 시스템 프롬프트 |
| 6 | app/rate_limiter.py | Redis rate limit |
| 7 | app/claude_client.py | Claude API 클라이언트 |
| 8 | app/main.py | FastAPI 앱 조립 |
| 9 | Dockerfile | 컨테이너화 |

---

## 주의사항

- `anthropic` Python SDK는 네이티브 async를 지원하므로 `AsyncAnthropic`을 사용한다.
- Redis도 `redis.asyncio`를 사용하여 완전 비동기로 동작한다.
- Kotlin 버전과 API 인터페이스(경로, 요청/응답 형식)를 동일하게 유지한다.
- 단, request body의 `siteId`는 Python 컨벤션에 따라 `site_id`로 변경했다. 프론트엔드와 맞춰야 한다면 Pydantic alias를 사용할 것:

```python
class DesignRequest(BaseModel):
    site_id: str = Field(alias="siteId")
    prompt: str

    model_config = {"populate_by_name": True}
```