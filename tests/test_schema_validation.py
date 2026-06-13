from demo.demo import run_demo
from demo.validate_output import validate_meal_decision


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
    }
]


def test_schema_validation_accepts_demo_output():
    result, _summary = run_demo(nearby_places=LIVE_NEARBY_PLACES)

    assert validate_meal_decision(result)
