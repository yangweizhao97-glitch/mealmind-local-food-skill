from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_TTL_SECONDS = 30 * 60


def request_json_with_cache(
    url: str,
    params: dict,
    timeout_seconds: float = 8,
    cache_namespace: str = "amap",
) -> dict:
    if os.getenv("MEALMIND_DISABLE_CACHE") == "1":
        return _request_json(url, params, timeout_seconds)

    ttl_seconds = int(os.getenv("MEALMIND_CACHE_TTL_SECONDS", str(DEFAULT_CACHE_TTL_SECONDS)))
    cache_path = _cache_path(url, params, cache_namespace)
    cached = _read_cache(cache_path, ttl_seconds)
    if cached is not None:
        return cached

    data = _request_json(url, params, timeout_seconds)
    _write_cache(cache_path, data)
    return data


def _request_json(url: str, params: dict, timeout_seconds: float) -> dict:
    request_url = f"{url}?{urlencode(params)}"
    with urlopen(request_url, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _cache_path(url: str, params: dict, namespace: str) -> Path:
    safe_params = {key: value for key, value in params.items() if key != "key"}
    cache_key = json.dumps({"url": url, "params": safe_params}, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
    return ROOT / "cache" / namespace / f"{digest}.json"


def _read_cache(path: Path, ttl_seconds: int) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    cached_at = payload.get("cached_at")
    if not isinstance(cached_at, (int, float)):
        return None
    if time.time() - cached_at > ttl_seconds:
        return None
    data = payload.get("data")
    return data if isinstance(data, dict) else None


def _write_cache(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cached_at": time.time(),
        "data": data,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
