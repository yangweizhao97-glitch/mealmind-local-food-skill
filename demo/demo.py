from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

try:
    from .meal_candidate_generator import generate_meal_candidates
    from .meal_scorer import score_candidates
    from .place_search import load_json, search_nearby_places
    from .recommendation_engine import build_recommendation, format_chinese_summary
    from .supermarket_value import analyze_nearby_store_intelligence
    from .time_context import contextualize_weather_for_meal, resolve_status_for_china_time
    from .validate_output import validate_meal_decision
    from .weather_provider import get_weather_context
except ImportError:
    from meal_candidate_generator import generate_meal_candidates
    from meal_scorer import score_candidates
    from place_search import load_json, search_nearby_places
    from recommendation_engine import build_recommendation, format_chinese_summary
    from supermarket_value import analyze_nearby_store_intelligence
    from time_context import contextualize_weather_for_meal, resolve_status_for_china_time
    from validate_output import validate_meal_decision
    from weather_provider import get_weather_context


ROOT = Path(__file__).resolve().parents[1]


def _load_config(default_relative_path: str, env_name: str) -> dict:
    configured_path = os.getenv(env_name)
    path = Path(configured_path).expanduser() if configured_path else ROOT / default_relative_path
    return load_json(path)


def run_demo(china_time: datetime | None = None, nearby_places: list[dict] | None = None) -> tuple[dict, str]:
    profile = _load_config("profiles/user_profile.json", "MEALMIND_USER_PROFILE_PATH")
    status = resolve_status_for_china_time(
        _load_config("data/today_status.json", "MEALMIND_TODAY_STATUS_PATH"),
        china_time,
    )
    weather_context = contextualize_weather_for_meal(
        get_weather_context(profile),
        status["meal_type"],
    )
    evidence_rules = load_json(ROOT / "data" / "evidence_rules.json")
    nearby_places = nearby_places if nearby_places is not None else search_nearby_places(profile)
    supermarket_value_context = analyze_nearby_store_intelligence(nearby_places)
    candidates = generate_meal_candidates(nearby_places)
    if not candidates:
        raise RuntimeError(
            "缺少实时餐馆/超市 POI 情报，无法生成真实推荐。请设置 AMAP_WEB_SERVICE_KEY 后运行。"
        )
    scored = score_candidates(candidates, profile, status, nearby_places, weather_context)
    result = build_recommendation(
        scored,
        profile,
        status,
        nearby_places,
        weather_context,
        evidence_rules,
        supermarket_value_context,
    )
    validate_meal_decision(result)
    return result, format_chinese_summary(result)


def main() -> None:
    try:
        result, summary = run_demo()
    except RuntimeError as error:
        print(str(error))
        print("示例菜单 fallback 已移除；请提供 AMAP_WEB_SERVICE_KEY 或注入授权来源 POI。")
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("\n--- 中文推荐总结 ---\n")
    print(summary)


if __name__ == "__main__":
    main()
