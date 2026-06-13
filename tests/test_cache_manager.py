import json

from demo import cache_manager


def test_request_json_with_cache_reuses_cached_response_and_excludes_key(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cache_manager, "ROOT", tmp_path)
    monkeypatch.setenv("MEALMIND_CACHE_TTL_SECONDS", "1800")

    def fake_request(url, params, timeout_seconds):
        calls.append((url, params, timeout_seconds))
        return {"status": "1", "result": "ok"}

    monkeypatch.setattr(cache_manager, "_request_json", fake_request)

    first = cache_manager.request_json_with_cache(
        "https://example.com/api",
        {"key": "secret-key", "city": "330106"},
        cache_namespace="test",
    )
    second = cache_manager.request_json_with_cache(
        "https://example.com/api",
        {"key": "secret-key", "city": "330106"},
        cache_namespace="test",
    )

    assert first == second == {"status": "1", "result": "ok"}
    assert len(calls) == 1
    cache_files = list((tmp_path / "cache" / "test").glob("*.json"))
    assert len(cache_files) == 1
    assert "secret-key" not in cache_files[0].read_text(encoding="utf-8")
    assert json.loads(cache_files[0].read_text(encoding="utf-8"))["data"] == first
