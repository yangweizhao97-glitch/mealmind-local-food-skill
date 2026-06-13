from datetime import datetime
from zoneinfo import ZoneInfo

from demo.demo import run_demo


LIVE_NEARBY_PLACES = [
    {
        "name": "真实兰州牛肉面",
        "type": "restaurant",
        "distance_m": 430,
        "rating": 4.4,
        "avg_cost_cny": 23,
        "signature_dishes": ["牛肉面", "凉拌牛肉"],
        "menu_items": [],
        "menu_data_status": "amap_poi_no_full_menu",
        "source": "authorized_map_api",
    },
]


def test_run_demo_returns_required_recommendations():
    result, summary = run_demo(
        datetime(2026, 6, 13, 12, 0, tzinfo=ZoneInfo("Asia/Shanghai")),
        nearby_places=LIVE_NEARBY_PLACES,
    )

    assert "top_recommendation" in result
    assert "restaurant_intelligence" in result
    assert "drink_recommendation" in result
    assert "not_recommended_today" in result
    assert result["top_recommendation"]["meal_name"]
    assert result["top_recommendation"]["place"] == "真实兰州牛肉面"
    assert result["top_recommendation"]["place_rating"] == 4.4
    assert result["top_recommendation"]["health_and_context_reasons"]
    assert result["user_state_summary"]["meal_type"] == "lunch"
    assert "今天午餐推荐" in summary
    assert "身体和情境理由" in summary
