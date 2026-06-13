from __future__ import annotations


def _walk_minutes_for_place(place_name: str, nearby_places: list[dict]) -> int | None:
    matched = [
        place
        for place in nearby_places
        if place_name in place.get("name", "") or place.get("name", "") in place_name
    ]
    if not matched:
        return None
    return round(min(place["distance_m"] for place in matched) / 80)


def _value_level(price: float, reference_price: float | None) -> str:
    if not reference_price:
        return "unknown"
    ratio = price / reference_price
    if ratio <= 0.85:
        return "very_good"
    if ratio <= 0.95:
        return "good"
    if ratio <= 1.05:
        return "normal"
    return "expensive"


def analyze_supermarket_value(
    food_sources: dict,
    parsed_local_prices: dict | None,
    nearby_places: list[dict],
) -> dict:
    supermarket_source = food_sources["supermarket_prices"][0]
    current_items = parsed_local_prices["items"] if parsed_local_prices else supermarket_source["items"]
    place_name = parsed_local_prices.get("store_name") if parsed_local_prices else supermarket_source["place_name"]
    source_type = parsed_local_prices.get("source_type") if parsed_local_prices else "fixture_price_table"
    reference_by_name = {
        item["name"]: item.get("reference_price_cny")
        for item in supermarket_source["items"]
    }

    analyzed_items = []
    for item in current_items:
        price = float(item["price_cny"])
        reference_price = item.get("reference_price_cny") or reference_by_name.get(item["name"])
        level = _value_level(price, reference_price)
        analyzed_items.append(
            {
                "name": item["name"],
                "price_cny": price,
                "unit": item.get("unit", ""),
                "reference_price_cny": reference_price,
                "value_level": level,
                "saving_cny": round(reference_price - price, 1) if reference_price else None,
            }
        )

    good_items = [
        item for item in analyzed_items if item["value_level"] in {"very_good", "good"}
    ]
    good_items = sorted(good_items, key=lambda item: item["saving_cny"] or 0, reverse=True)
    best_names = "、".join(item["name"] for item in good_items[:3])
    summary = (
        f"{place_name} 今天性价比较高的是 {best_names}"
        if best_names
        else f"{place_name} 今天没有明显低于参考价的菜"
    )

    return {
        "place_name": place_name,
        "source_type": source_type,
        "walk_minutes_from_home": _walk_minutes_for_place(place_name, nearby_places),
        "is_live_price": source_type not in {"manual_text", "fixture_price_table"},
        "summary": summary,
        "good_value_items": good_items[:5],
        "all_checked_items": analyzed_items,
    }


def analyze_nearby_store_intelligence(nearby_places: list[dict]) -> dict:
    stores = [
        place
        for place in nearby_places
        if place.get("type") in {"supermarket", "convenience_store"}
    ]
    stores = sorted(stores, key=lambda place: place.get("distance_m") or 10**9)
    if not stores:
        return {
            "summary": "实时地图未返回附近超市或便利店。",
            "stores": [],
            "promotion_status": "not_found",
            "good_value_items": [],
        }

    nearest = stores[0]
    walk_minutes = nearest.get("walking_minutes") or round((nearest.get("distance_m") or 0) / 80)
    return {
        "summary": (
            f"最近的超市/便利店是 {nearest['name']}，离住处约步行 {walk_minutes} 分钟；"
            "高德 POI 未提供具体活动和单品菜价。"
        ),
        "stores": [
            {
                "name": store["name"],
                "type": store.get("type"),
                "distance_m": store.get("distance_m"),
                "walk_minutes_from_home": store.get("walking_minutes") or round((store.get("distance_m") or 0) / 80),
                "walking_distance_m": store.get("walking_distance_m"),
                "amap_linear_distance_m": store.get("amap_linear_distance_m"),
                "rating": store.get("rating"),
                "avg_cost_cny": store.get("avg_cost_cny"),
                "source": store.get("source"),
                "promotion_status": "amap_poi_no_promotion_data",
                "menu_data_status": store.get("menu_data_status", "amap_poi_no_full_menu"),
            }
            for store in stores[:5]
        ],
        "promotion_status": "amap_poi_no_promotion_data",
        "good_value_items": [],
    }
