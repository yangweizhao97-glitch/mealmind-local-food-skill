from __future__ import annotations


def generate_meal_candidates(nearby_places: list[dict] | None = None) -> list[dict]:
    places = [
        place
        for place in (nearby_places or [])
        if place.get("source") == "authorized_map_api"
        and place.get("type") in {"restaurant", "convenience_store", "supermarket", "drink_shop"}
        and _is_recommendable_place(place)
    ]
    candidates = []
    for place in places:
        candidates.extend(_menu_item_candidates(place))
        if not place.get("menu_items"):
            candidates.extend(_signature_or_store_candidates(place))
    return candidates


def _menu_item_candidates(place: dict) -> list[dict]:
    candidates = []
    for item in place.get("menu_items", [])[:5]:
        price = item.get("price_cny")
        if price is None:
            continue
        meal_name = item["name"]
        candidates.append(
            _candidate_from_place(
                place=place,
                meal_name=meal_name,
                price=float(price),
                tags=_infer_food_tags(meal_name, place),
                reason=f"高德 POI 返回了菜单字段，检测到 {meal_name} 价格约 {price:g} 元。",
                price_source="amap_menu_field",
                confidence="中",
            )
        )
    return candidates


def _signature_or_store_candidates(place: dict) -> list[dict]:
    if place.get("type") == "restaurant":
        return _restaurant_signature_candidates(place)
    return [_store_visit_candidate(place)]


def _restaurant_signature_candidates(place: dict) -> list[dict]:
    dishes = place.get("signature_dishes") or []
    has_signature = bool(dishes)
    if not has_signature:
        dishes = [f"{place['name']} 到店热食/简餐"]

    candidates = []
    for dish in dishes[:5]:
        has_avg_cost = place.get("avg_cost_cny") is not None
        price = float(place.get("avg_cost_cny") or 30)
        if has_signature and has_avg_cost:
            price_source = "amap_avg_cost_estimate"
            confidence = "中"
            reason = (
                f"高德 POI 显示该店招牌/特色包含 {dish}；"
                f"评分 {place.get('rating') or '未知'}，人均约 {price:g} 元。"
            )
        elif has_avg_cost and (place.get("rating") or 0) >= 4.0:
            price_source = "amap_avg_cost_estimate"
            confidence = "中"
            reason = (
                "高德 POI 未返回招牌菜和完整菜单价，"
                f"但返回评分 {place.get('rating')}、人均约 {price:g} 元；适合作为近距离热食备选。"
            )
        else:
            price_source = "amap_poi_no_menu_price"
            confidence = "低"
            reason = (
                f"高德 POI 返回了该店，但未返回完整菜单价"
                f"{'和人均消费' if not has_avg_cost else ''}；评分 {place.get('rating') or '未知'}。"
            )
        candidates.append(
            _candidate_from_place(
                place=place,
                meal_name=dish,
                price=price,
                tags=_infer_food_tags(dish, place),
                reason=reason,
                price_source=price_source,
                confidence=confidence,
            )
        )
    return candidates


def _store_visit_candidate(place: dict) -> dict:
    price = float(place.get("avg_cost_cny") or 20)
    if place.get("type") == "convenience_store":
        meal_name = f"{place['name']} 便利店即食组合"
        tags = ["quick", "value", "protein"]
        reason = "高德返回了附近便利店 POI；开放 API 未返回具体活动或单品价格，需以门店/小程序为准。"
    elif place.get("type") == "supermarket":
        meal_name = f"{place['name']} 超市熟食/即食组合"
        tags = ["value", "vegetable", "protein"]
        reason = "高德返回了附近超市 POI；开放 API 未返回今日菜价和活动，需以门店价签为准。"
    else:
        meal_name = f"{place['name']} 饮品"
        tags = ["drink"]
        reason = "高德返回了附近饮品店 POI；开放 API 未返回具体饮品价格，需以门店菜单为准。"

    return _candidate_from_place(
        place=place,
        meal_name=meal_name,
        price=price,
        tags=tags,
        reason=reason,
        price_source="amap_poi_no_menu_price",
        confidence="低",
    )


def _is_recommendable_place(place: dict) -> bool:
    rating = place.get("rating")
    if rating is not None and rating < 3.5:
        return False
    return True


def _candidate_from_place(
    place: dict,
    meal_name: str,
    price: float,
    tags: list[str],
    reason: str,
    price_source: str,
    confidence: str,
) -> dict:
    return {
        "meal_name": meal_name,
        "place": place["name"],
        "items": [meal_name],
        "category": _candidate_category_for_place(place, price),
        "tags": sorted(set(tags)),
        "estimated_price_value": round(price, 1),
        "estimated_price_cny": _price_text(price, price_source),
        "estimated_calories": "450-800 kcal",
        "estimated_protein": "20-40 g" if "protein" in tags else "10-30 g",
        "satiety_prediction": "3-5 hours",
        "reason": reason,
        "ordering_keywords": f"{place['name']} {meal_name}",
        "copyable_note": "少油，不要香菜；单品价格以店内实时菜单为准。",
        "price_source": price_source,
        "source_confidence": confidence,
        "place_rating": place.get("rating"),
        "place_avg_cost_cny": place.get("avg_cost_cny"),
        "place_distance_m": place.get("distance_m"),
        "place_walking_distance_m": place.get("walking_distance_m"),
        "place_walking_minutes": place.get("walking_minutes"),
        "place_linear_distance_m": place.get("amap_linear_distance_m"),
        "place_signature_dishes": place.get("signature_dishes", []),
        "place_menu_data_status": place.get("menu_data_status", "unknown"),
    }


def _candidate_category_for_place(place: dict, price: float) -> str:
    place_type = place.get("type")
    if place_type == "drink_shop":
        return "drink"
    if place_type == "convenience_store":
        return "convenience"
    if place_type == "supermarket":
        return "supermarket"
    if price >= 45:
        return "premium"
    return "restaurant"


def _price_text(price: float, price_source: str) -> str:
    if price_source == "amap_menu_field":
        return f"{price:g}"
    if price_source == "amap_avg_cost_estimate":
        return f"人均约 {price:g}"
    return "未返回单品价格"


def _infer_food_tags(meal_name: str, place: dict) -> list[str]:
    text = f"{meal_name} {place.get('name', '')}"
    tags = []
    if any(keyword in text for keyword in ["牛", "鸡", "蛋", "鱼", "肉", "虾"]):
        tags.append("protein")
    if any(keyword in text for keyword in ["饭", "面", "粉", "粥", "包", "饼", "米线"]):
        tags.extend(["hot_meal", "carb"])
    if any(keyword in text for keyword in ["沙拉", "蔬", "菜", "西兰花"]):
        tags.append("vegetable")
    if any(keyword in text for keyword in ["无糖", "茶", "咖啡", "豆浆"]):
        tags.extend(["drink", "low_sugar"])
    if not tags and place.get("type") == "restaurant":
        tags.extend(["hot_meal", "balanced"])
    if any(keyword in text for keyword in ["食堂", "餐厅", "简餐"]):
        tags.extend(["hot_meal", "balanced"])
    return tags
