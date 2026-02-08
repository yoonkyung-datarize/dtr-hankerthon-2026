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
    match = DATA_URL_PATTERN.search(prompt)
    if match:
        mime_type = f"image/{match.group(1)}"
        base64_data = match.group(2)
        text_only = prompt.replace(match.group(0), "").strip()
        return text_only, base64_data, mime_type
    return prompt, None, None


def strip_code_fences(text: str) -> str:
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
