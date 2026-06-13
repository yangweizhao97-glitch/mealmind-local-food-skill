from __future__ import annotations


WEIGHTS = {
    "goal_match": 0.20,
    "nutrition_structure": 0.16,
    "price_value": 0.15,
    "distance_convenience": 0.12,
    "weather_match": 0.10,
    "mood_body_match": 0.12,
    "taste_preference": 0.08,
    "data_confidence": 0.07,
}


def _budget(profile: dict, status: dict) -> float:
    budgets = profile["budget_profile"]
    if status.get("want_better_food") or status.get("today_goal") == "premium":
        return budgets["premium_meal_budget_cny"]
    if status.get("today_goal") == "budget_saving":
        return budgets["budget_saving_meal_budget_cny"]
    return budgets["normal_meal_budget_cny"]


def _has_any(tags: set[str], wanted: set[str]) -> bool:
    return bool(tags.intersection(wanted))


def _candidate_places(candidate: dict) -> list[str]:
    return [part.strip() for part in candidate.get("place", "").split("+") if part.strip()]


def _matched_places(candidate: dict, nearby_places: list[dict] | None) -> list[dict]:
    if not nearby_places:
        return []
    names = _candidate_places(candidate)
    exact_matched = []
    for place in nearby_places:
        place_name = place.get("name", "")
        if any(name == place_name for name in names):
            exact_matched.append(place)
    if exact_matched:
        return exact_matched

    matched = []
    for place in nearby_places:
        place_name = place.get("name", "")
        if any(name in place_name or place_name in name for name in names):
            matched.append(place)
    return matched


def _distance_score(candidate: dict, profile: dict, nearby_places: list[dict] | None, weather: dict | None) -> float:
    matched = _matched_places(candidate, nearby_places)
    if not matched:
        return 72 if candidate["category"] in {"convenience", "drink"} else 64

    max_walk_minutes = profile["lifestyle"].get("max_walk_time_minutes", 12)
    distance_m = min(place["distance_m"] for place in matched)
    walk_minutes = distance_m / 80
    score = 100 - max(0, walk_minutes - 3) * 4
    if walk_minutes > max_walk_minutes:
        score -= 30

    weather_impacts = set((weather or {}).get("meal_impact", []))
    if "rain_reduce_walking" in weather_impacts and walk_minutes > 8:
        score -= 12
    if candidate["category"] in {"convenience", "drink"}:
        score += 6
    return _clamp(score)


def _weather_score(tags: set[str], candidate: dict, weather: dict | None) -> float:
    if not weather:
        return 70

    score = 70
    impacts = set(weather.get("meal_impact", []))
    temperature = weather.get("temperature_c")

    if "cold_prefer_hot_meal" in impacts or (temperature is not None and temperature <= 14):
        score += 16 if "hot_meal" in tags else -8
        score += 5 if _has_any(tags, {"protein", "balanced"}) else 0
        if candidate["category"] == "drink" and "coffee" in tags:
            score -= 8
    if "rain_reduce_walking" in impacts:
        score += 8 if candidate["category"] in {"convenience", "restaurant"} else 0
    if temperature is not None and temperature >= 28:
        score += 10 if _has_any(tags, {"low_sugar", "quick"}) else 0
        score -= 10 if "heavy_oil" in tags else 0

    return _clamp(score)


def _mood_body_score(tags: set[str], candidate: dict, status: dict) -> float:
    score = 62
    mood = status.get("mood")
    hunger = status.get("hunger_level", 5)
    stress = status.get("stress_level", 5)
    energy = status.get("energy_level", 5)

    if hunger >= 7:
        score += 14 if "hot_meal" in tags else -8
        score += 10 if "protein" in tags else -6
        score += 6 if _has_any(tags, {"rice", "carb", "fiber"}) else 0
    if mood in {"tired", "low_mood"} or energy <= 4:
        score += 14 if "hot_meal" in tags else 0
        score += 6 if _has_any(tags, {"balanced", "protein"}) else 0
    if mood == "stressed" or stress >= 7:
        score += 8 if _has_any(tags, {"hot_meal", "balanced", "premium"}) else 0
        score -= 12 if "sweetened" in tags else 0
    if status.get("exercised_today"):
        score += 10 if "protein" in tags else -4
        score += 4 if _has_any(tags, {"rice", "carb"}) else 0
    if status.get("meal_type") == "dinner" and candidate["category"] == "drink" and "coffee" in tags:
        score -= 8

    return _clamp(score)


def _data_confidence(candidate: dict, nearby_places: list[dict] | None, weather: dict | None) -> float:
    score = 68
    score += 10 if candidate.get("estimated_price_value", 0) > 0 else -12
    score += 10 if _matched_places(candidate, nearby_places) else 0
    score += 8 if weather and weather.get("data_freshness") else 0
    price_source = candidate.get("price_source")
    if price_source == "amap_menu_field":
        score += 12
    elif price_source == "amap_avg_cost_estimate":
        score += 4
    elif price_source == "amap_poi_no_menu_price":
        score -= 35
    rating = candidate.get("place_rating")
    if rating is not None:
        score += 8 if rating >= 4.2 else 4
        if rating < 3.5:
            score -= 16
    if candidate.get("place_avg_cost_cny") is not None:
        score += 4
    if candidate.get("source_confidence") == "低":
        score -= 15
    if (weather or {}).get("source") == "mock_weather":
        score -= 4
    return _clamp(score)


def score_candidate(
    candidate: dict,
    profile: dict,
    status: dict,
    nearby_places: list[dict] | None = None,
    weather: dict | None = None,
) -> dict:
    tags = set(candidate.get("tags", []))
    price = float(candidate["estimated_price_value"])
    budget = _budget(profile, status)
    goal = status.get("today_goal", profile["diet_preferences"].get("main_goal"))

    goal_match = 60
    if goal in {"fat_loss", "fat_loss_but_not_hungry"}:
        goal_match += 18 if "protein" in tags else -12
        goal_match += 10 if "low_sugar" in tags else -5
        goal_match += 8 if _has_any(tags, {"vegetable", "fiber"}) else 0
        goal_match += 8 if status.get("hunger_level", 5) >= 7 and "hot_meal" in tags else 0
        goal_match -= 20 if "sweetened" in tags else 0
    elif goal == "budget_saving":
        goal_match += 20 if price <= budget else -15
        goal_match += 8 if _has_any(tags, {"budget", "value", "quick"}) else 0
    elif goal == "premium":
        goal_match += 24 if "premium" in tags else -6
    elif goal in {"muscle_gain", "high_energy"}:
        goal_match += 18 if "protein" in tags else 0
        goal_match += 8 if _has_any(tags, {"rice", "carb"}) else 0

    price_value = 100 if price <= budget else max(35, 100 - (price - budget) * 4)
    if candidate.get("price_source") == "amap_poi_no_menu_price":
        price_value = min(price_value, 55)
    nutrition_structure = 45
    nutrition_structure += 25 if "protein" in tags else 0
    nutrition_structure += 15 if _has_any(tags, {"carb", "rice", "fiber"}) else 0
    nutrition_structure += 15 if _has_any(tags, {"vegetable", "low_sugar"}) else 0
    nutrition_structure -= 22 if "sweetened" in tags else 0

    distance_convenience = _distance_score(candidate, profile, nearby_places, weather)
    if candidate["category"] == "supermarket" and not profile["lifestyle"].get("can_cook"):
        distance_convenience -= 12

    names = "".join(candidate.get("items", []))
    likes = profile["diet_preferences"].get("likes", [])
    dislikes = profile["diet_preferences"].get("dislikes", [])
    allergies = profile["diet_preferences"].get("allergies", [])
    taste_preference = 68 + sum(6 for like in likes if like in names)
    taste_preference -= sum(18 for dislike in dislikes if dislike in names)
    taste_preference -= sum(100 for allergy in allergies if allergy in names)

    components = {
        "goal_match": _clamp(goal_match),
        "nutrition_structure": _clamp(nutrition_structure),
        "price_value": _clamp(price_value),
        "distance_convenience": _clamp(distance_convenience),
        "weather_match": _weather_score(tags, candidate, weather),
        "mood_body_match": _mood_body_score(tags, candidate, status),
        "taste_preference": _clamp(taste_preference),
        "data_confidence": _data_confidence(candidate, nearby_places, weather),
    }
    total_score = round(sum(components[key] * WEIGHTS[key] for key in WEIGHTS))

    scored = dict(candidate)
    scored["score_components"] = components
    scored["total_score"] = int(_clamp(total_score))
    return scored


def score_candidates(
    candidates: list[dict],
    profile: dict,
    status: dict,
    nearby_places: list[dict] | None = None,
    weather: dict | None = None,
) -> list[dict]:
    return sorted(
        [score_candidate(candidate, profile, status, nearby_places, weather) for candidate in candidates],
        key=lambda candidate: candidate["total_score"],
        reverse=True,
    )


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))
