from datetime import datetime
from zoneinfo import ZoneInfo

from demo.time_context import (
    contextualize_weather_for_meal,
    infer_meal_type_from_china_time,
    resolve_status_for_china_time,
)


TZ = ZoneInfo("Asia/Shanghai")


def test_infer_meal_type_from_noon_china_time():
    assert infer_meal_type_from_china_time(datetime(2026, 6, 13, 12, 0, tzinfo=TZ)) == "lunch"


def test_resolve_status_overrides_static_meal_type_with_china_time():
    status = {"meal_type": "dinner", "today_goal": "fat_loss"}

    resolved = resolve_status_for_china_time(status, datetime(2026, 6, 13, 12, 0, tzinfo=TZ))

    assert resolved["meal_type"] == "lunch"
    assert resolved["time_context"]["timezone"] == "Asia/Shanghai"
    assert resolved["time_context"]["meal_type_source"] == "china_time_auto"
    assert resolved["time_context"]["original_meal_type"] == "dinner"


def test_contextualize_weather_summary_for_lunch():
    weather = {
        "meal_impact": ["rain_reduce_walking", "avoid_iced_drinks_at_dinner"],
        "summary": "小雨，体感偏冷，晚餐优先近距离热食和低糖热饮。",
    }

    contextualized = contextualize_weather_for_meal(weather, "lunch")

    assert contextualized["summary"] == "小雨，体感偏冷，午餐优先近距离热食和低糖热饮。"
    assert "avoid_iced_drinks_at_dinner" not in contextualized["meal_impact"]
