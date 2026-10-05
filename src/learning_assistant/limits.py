"""In-process rate limit + exact-query cache (no Redis)."""
import hashlib
import time
from collections import defaultdict
from datetime import date, datetime, timezone
from threading import Lock

from learning_assistant.config import settings

_hits: dict[str, list[float]] = defaultdict(list)
_cache: dict[str, tuple[float, dict]] = {}
_guest_questions: dict[str, date] = {}
_guest_questions_lock = Lock()


def _utc_today() -> date:
    return datetime.now(timezone.utc).date()


def allow(key: str) -> bool:
    now = time.time()
    recent = [t for t in _hits[key] if now - t < 60]
    if len(recent) >= settings.RATE_LIMIT_PER_MINUTE:
        _hits[key] = recent
        return False
    recent.append(now)
    _hits[key] = recent
    return True


def allow_guest_question(ip_address: str) -> bool:
    today = _utc_today()
    with _guest_questions_lock:
        expired_ips = [
            address for address, question_date in _guest_questions.items()
            if question_date != today
        ]
        for address in expired_ips:
            del _guest_questions[address]

        if _guest_questions.get(ip_address) == today:
            return False
        _guest_questions[ip_address] = today
        return True


def _ckey(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode()).hexdigest()


def cache_get(query: str) -> dict | None:
    item = _cache.get(_ckey(query))
    if not item:
        return None
    ts, val = item
    if time.time() - ts > settings.CACHE_TTL_SECONDS:
        _cache.pop(_ckey(query), None)
        return None
    return val


def cache_set(query: str, val: dict) -> None:
    _cache[_ckey(query)] = (time.time(), val)
