import time
from collections import defaultdict
from app.config import settings
from app.exceptions import RateLimitExceededException

_store: dict[str, list[float]] = defaultdict(list)


async def check_and_increment(site_id: str):
    now = time.time()
    window = settings.rate_limit_ttl_hours * 3600
    key = site_id

    # Expire old entries
    _store[key] = [t for t in _store[key] if now - t < window]

    if len(_store[key]) >= settings.max_requests_per_site:
        raise RateLimitExceededException(
            f"사이트 {site_id} 의 일일 요청 한도({settings.max_requests_per_site}회)를 초과했습니다."
        )

    _store[key].append(now)
