import json
import os
import time
import urllib.request
from typing import Any, Optional

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")


def _upstash(command: list) -> Any:
    """Fire-and-forget HTTP call to Upstash REST API."""
    if not UPSTASH_URL:
        return None

    url = f"{UPSTASH_URL}/{'/'.join(str(chunk) for chunk in command)}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=1) as response:
            return json.loads(response.read()).get("result")
    except Exception:
        return None


def cache_get(key: str) -> Optional[str]:
    return _upstash(["GET", key])


def cache_set(key: str, value: str, ex: int = 60) -> None:
    _upstash(["SET", key, value, "EX", ex])


def cache_del(key: str) -> None:
    _upstash(["DEL", key])
