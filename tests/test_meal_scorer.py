from demo.meal_scorer import score_candidate


PROFILE = {
    "diet_preferences": {"main_goal": "fat_loss", "likes": ["牛肉"], "dislikes": ["香菜"], "allergies": []},
    "budget_profile": {"normal_meal_budget_cny": 30, "premium_meal_budget_cny": 60, "budget_saving_meal_budget_cny": 20},
    "lifestyle": {"can_cook": False},
}

STATUS = {
    "today_goal": "fat_loss_but_not_hungry",
    "hunger_level": 8,
    "work_intensity": "high",
    "exercised_today": False,
    "mood": "tired",
}


def test_score_candidate_rewards_hot_protein_low_sugar():
    candidate = {
        "meal_name": "牛肉面小份 + 加牛肉 + 无糖茶",
        "items": ["牛肉面小份", "加牛肉", "无糖茶"],
        "category": "restaurant",
        "tags": ["hot_meal", "protein", "low_sugar", "beef"],
        "estimated_price_value": 28,
    }

    scored = score_candidate(candidate, PROFILE, STATUS)

    assert scored["total_score"] >= 80
    assert scored["score_components"]["goal_match"] > 80


def test_score_candidate_penalizes_poi_without_menu_price():
    base_candidate = {
        "meal_name": "牛肉饭小份",
        "items": ["牛肉饭小份"],
        "category": "restaurant",
        "tags": ["hot_meal", "protein", "carb"],
        "estimated_price_value": 22,
        "place": "真实简餐店",
        "place_rating": 4.5,
        "place_avg_cost_cny": 25,
    }
    menu_candidate = {
        **base_candidate,
        "price_source": "amap_menu_field",
        "source_confidence": "中",
    }
    no_price_candidate = {
        **base_candidate,
        "price_source": "amap_poi_no_menu_price",
        "source_confidence": "低",
    }

    menu_scored = score_candidate(menu_candidate, PROFILE, STATUS)
    no_price_scored = score_candidate(no_price_candidate, PROFILE, STATUS)

    assert menu_scored["score_components"]["data_confidence"] > no_price_scored["score_components"]["data_confidence"]
    assert no_price_scored["score_components"]["price_value"] <= 55
