from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo


CHINA_TIMEZONE = "Asia/Shanghai"


def current_china_time() -> datetime:
    return datetime.now(ZoneInfo(CHINA_TIMEZONE))


def infer_meal_type_from_china_time(china_time: datetime) -> str:
    hour = china_time.hour
    if 5 <= hour < 10:
        return "breakfast"
    if 10 <= hour < 14:
        return "lunch"
    if 14 <= hour < 16:
        return "snack"
    if 16 <= hour < 21:
        return "dinner"
    return "late_snack"


def resolve_status_for_china_time(status: dict, china_time: datetime | None = None) -> dict:
    china_time = china_time or current_china_time()
    resolved = deepcopy(status)
    original_meal_type = resolved.get("meal_type")
    resolved["meal_type"] = infer_meal_type_from_china_time(china_time)
    resolved["time_context"] = {
        "timezone": CHINA_TIMEZONE,
        "china_time": china_time.isoformat(timespec="minutes"),
        "meal_type_source": "china_time_auto",
        "original_meal_type": original_meal_type,
    }
    return resolved


def contextualize_weather_for_meal(weather_context: dict | None, meal_type: str) -> dict | None:
    if not weather_context:
        return weather_context

    meal_type_cn = {
        "breakfast": "早餐",
        "lunch": "午餐",
        "snack": "加餐",
        "dinner": "晚餐",
        "late_snack": "夜间加餐",
    }.get(meal_type, "本餐")

    contextualized = deepcopy(weather_context)
    impacts = contextualized.get("meal_impact", [])
    if meal_type != "dinner":
        contextualized["meal_impact"] = [
            impact for impact in impacts if impact != "avoid_iced_drinks_at_dinner"
        ]

    summary = contextualized.get("summary")
    if summary:
        contextualized["summary"] = (
            summary.replace("晚餐", meal_type_cn)
            .replace("本餐", meal_type_cn)
        )
    return contextualized
