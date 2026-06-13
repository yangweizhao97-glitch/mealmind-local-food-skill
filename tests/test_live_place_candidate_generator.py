from demo.meal_candidate_generator import generate_meal_candidates


def test_generate_candidates_from_live_amap_places():
    nearby_places = [
        {
            "name": "真实兰州牛肉面",
            "type": "restaurant",
            "distance_m": 430,
            "rating": 4.4,
            "avg_cost_cny": 23,
            "signature_dishes": ["牛肉面", "凉拌牛肉"],
            "menu_items": [],
            "source": "authorized_map_api",
        }
    ]

    candidates = generate_meal_candidates(nearby_places)

    assert candidates[0]["place"] == "真实兰州牛肉面"
    assert candidates[0]["meal_name"] == "牛肉面"
    assert candidates[0]["estimated_price_cny"] == "人均约 23"
    assert candidates[0]["price_source"] == "amap_avg_cost_estimate"
    assert candidates[0]["place_distance_m"] == 430


def test_generate_candidates_prefers_menu_item_prices_when_present():
    nearby_places = [
        {
            "name": "真实简餐店",
            "type": "restaurant",
            "distance_m": 260,
            "rating": 4.6,
            "avg_cost_cny": 30,
            "signature_dishes": ["牛肉饭"],
            "menu_items": [{"name": "牛肉饭小份", "price_cny": 19.9}],
            "source": "authorized_map_api",
        }
    ]

    candidates = generate_meal_candidates(nearby_places)

    assert candidates[0]["meal_name"] == "牛肉饭小份"
    assert candidates[0]["estimated_price_cny"] == "19.9"
    assert candidates[0]["price_source"] == "amap_menu_field"


def test_generate_candidates_marks_restaurant_without_cost_or_signature_as_low_confidence():
    nearby_places = [
        {
            "name": "真实小炒店",
            "type": "restaurant",
            "distance_m": 120,
            "rating": 3.6,
            "avg_cost_cny": None,
            "signature_dishes": [],
            "menu_items": [],
            "source": "authorized_map_api",
        }
    ]

    candidates = generate_meal_candidates(nearby_places)

    assert candidates[0]["meal_name"] == "真实小炒店 到店热食/简餐"
    assert candidates[0]["price_source"] == "amap_poi_no_menu_price"
    assert candidates[0]["source_confidence"] == "低"
    assert candidates[0]["estimated_price_cny"] == "未返回单品价格"


def test_generate_candidates_filters_low_rating_places():
    nearby_places = [
        {
            "name": "低评分米线",
            "type": "restaurant",
            "distance_m": 80,
            "rating": 1.2,
            "avg_cost_cny": None,
            "signature_dishes": [],
            "menu_items": [],
            "source": "authorized_map_api",
        }
    ]

    assert generate_meal_candidates(nearby_places) == []


def test_generate_candidates_allows_high_rating_canteen_with_avg_cost():
    nearby_places = [
        {
            "name": "西和公寓食堂",
            "type": "restaurant",
            "distance_m": 75,
            "rating": 4.5,
            "avg_cost_cny": 13,
            "signature_dishes": [],
            "menu_items": [],
            "source": "authorized_map_api",
        }
    ]

    candidates = generate_meal_candidates(nearby_places)

    assert candidates[0]["meal_name"] == "西和公寓食堂 到店热食/简餐"
    assert candidates[0]["price_source"] == "amap_avg_cost_estimate"
    assert candidates[0]["source_confidence"] == "中"
