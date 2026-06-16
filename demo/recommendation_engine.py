from __future__ import annotations


SAFETY_NOTE = "这是日常饮食建议，不是医疗诊断。如有疾病、孕期、进食障碍风险或特殊饮食限制，应咨询专业人士。"


def _pick(scored: list[dict], predicate, fallback: dict | None = None) -> dict:
    for candidate in scored:
        if predicate(candidate):
            return candidate
    return fallback or scored[0]


def _option(candidate: dict, score_key: str = "score") -> dict:
    return {
        "meal_name": candidate["meal_name"],
        "place": candidate["place"],
        score_key: candidate["total_score"],
        "estimated_price_cny": candidate["estimated_price_cny"],
        "reason": candidate["reason"],
    }


def _walk_minutes_for(candidate: dict, nearby_places: list[dict]) -> int | None:
    names = [part.strip() for part in candidate.get("place", "").split("+") if part.strip()]
    exact_matched = [
        place
        for place in nearby_places
        if any(name == place.get("name", "") for name in names)
    ]
    matched = exact_matched or [
        place
        for place in nearby_places
        if any(name in place.get("name", "") or place.get("name", "") in name for name in names)
    ]
    if not matched:
        return None
    walking_minutes = [
        place.get("walking_minutes")
        for place in matched
        if place.get("walking_minutes") is not None
    ]
    if walking_minutes:
        return min(walking_minutes)
    return round(min(place["distance_m"] for place in matched) / 80)


def _evidence_summary(evidence_rules: dict | None) -> dict:
    rules = (evidence_rules or {}).get("rules", [])
    return {
        "knowledge_base": "curated_evidence_rules",
        "used_rules": [rule["id"] for rule in rules[:4]],
        "principle": "优先高质量饮食结构；心情状态只调整推荐倾向，不做医疗诊断。",
    }


def _meal_type_label(meal_type: str) -> str:
    return {
        "breakfast": "早餐",
        "lunch": "午餐",
        "snack": "加餐",
        "dinner": "晚餐",
        "late_snack": "夜间加餐",
    }.get(meal_type, meal_type)


def _health_explanations(candidate: dict, status: dict, weather_context: dict | None, evidence_rules: dict | None) -> list[str]:
    tags = set(candidate.get("tags", []))
    weather_impacts = set((weather_context or {}).get("meal_impact", []))
    hunger = status.get("hunger_level", 5)
    walk_minutes = round((candidate.get("place_distance_m") or 0) / 80) if candidate.get("place_distance_m") is not None else None
    explanations = []

    for rule in (evidence_rules or {}).get("explanation_rules", []):
        if not _explanation_rule_matches(rule, candidate, tags, weather_impacts, hunger, walk_minutes):
            continue
        explanations.append(rule["text"])
        if len(explanations) >= 5:
            break

    if not explanations:
        explanations.append("这份推荐主要基于距离、天气、预算和当前身体状态综合评分。")
    return explanations


def _explanation_rule_matches(
    rule: dict,
    candidate: dict,
    tags: set[str],
    weather_impacts: set[str],
    hunger: int,
    walk_minutes: int | None,
) -> bool:
    trigger_tags = set(rule.get("trigger_tags", []))
    if trigger_tags and not tags.intersection(trigger_tags):
        return False
    trigger_weather = set(rule.get("trigger_weather_impacts", []))
    if trigger_weather and not weather_impacts.intersection(trigger_weather):
        return False
    if rule.get("min_hunger_level") is not None and hunger < rule["min_hunger_level"]:
        return False
    if rule.get("max_walk_minutes") is not None:
        if walk_minutes is None or walk_minutes > rule["max_walk_minutes"]:
            return False
    if rule.get("requires_rating") and candidate.get("place_rating") is None:
        return False
    if rule.get("requires_avg_cost") and candidate.get("place_avg_cost_cny") is None:
        return False
    trigger_price_sources = set(rule.get("trigger_price_sources", []))
    if trigger_price_sources and candidate.get("price_source") not in trigger_price_sources:
        return False
    return True


def _place_source_summary(nearby_places: list[dict]) -> dict:
    sources = sorted({place.get("source", "unknown") for place in nearby_places})
    is_live = any(source not in {"mock_fixture", "unknown"} for source in sources)
    return {
        "sources": sources,
        "is_live": is_live,
        "note": "当前为授权实时地图数据。" if is_live else "mock_fixture 只能用于离线测试，不能生成真实推荐。",
    }


def _restaurant_intelligence(nearby_places: list[dict]) -> dict:
    restaurants = [
        place for place in nearby_places if place.get("type") in {"restaurant", "drink_shop"}
    ]
    restaurants = sorted(restaurants, key=lambda place: place.get("distance_m") or 10**9)
    return {
        "methodology": {
            "distance": "离住处越近越好，雨天加权更高",
            "rating": "高德评分越高，好吃概率越高",
            "avg_cost": "高德人均消费只能估算预算，不等于单品价格",
            "signature_dishes": "高德 tag 字段作为招牌菜候选",
            "menu_price": "仅当高德返回 menu/foods/dishes 等字段时才视为单品价格",
        },
        "restaurants": [
            {
                "name": place.get("name"),
                "type": place.get("type"),
                "distance_m": place.get("distance_m"),
                "walk_minutes_from_home": place.get("walking_minutes") or round((place.get("distance_m") or 0) / 80),
                "walking_distance_m": place.get("walking_distance_m"),
                "amap_linear_distance_m": place.get("amap_linear_distance_m"),
                "rating": place.get("rating"),
                "avg_cost_cny": place.get("avg_cost_cny"),
                "signature_dishes": place.get("signature_dishes", []),
                "menu_items": place.get("menu_items", []),
                "menu_data_status": place.get("menu_data_status", "unknown"),
                "source": place.get("source"),
            }
            for place in restaurants[:8]
        ],
    }


def _store_purchase_plan(supermarket_value_context: dict | None, status: dict, top: dict) -> dict:
    context = supermarket_value_context or {}
    good_items = context.get("good_value_items") or []
    store_name = context.get("place_name")
    stores = context.get("stores") or []
    if not store_name and stores:
        store_name = stores[0].get("name")

    meal_type = status.get("meal_type")
    hunger = status.get("hunger_level", 5)
    if meal_type == "breakfast":
        default_items = ["鸡蛋", "全麦面包或燕麦", "无糖豆浆", "水果"]
        cook_plan = "鸡蛋燕麦/全麦早餐配无糖豆浆"
    elif meal_type == "snack":
        default_items = ["无糖酸奶", "香蕉", "坚果小包"]
        cook_plan = "酸奶水果坚果加餐"
    elif meal_type == "late_snack":
        default_items = ["鸡蛋", "青菜", "挂面或小馄饨", "无糖热饮"]
        cook_plan = "小份青菜鸡蛋汤面"
    elif hunger >= 7:
        default_items = ["鸡胸肉或鸡蛋", "青菜", "米饭或玉米", "无糖豆浆"]
        cook_plan = "鸡蛋/鸡胸肉青菜饭"
    else:
        default_items = ["鸡蛋", "豆腐", "青菜", "玉米"]
        cook_plan = "豆腐青菜鸡蛋轻食碗"

    value_item_names = [item["name"] for item in good_items[:3] if item.get("name")]
    shopping_list = value_item_names or default_items
    source_note = (
        "优先使用超市今日低于参考价的食材。"
        if value_item_names
        else "未拿到实时单品菜价，食材清单按通用健康组合生成。"
    )
    store_text = store_name or "附近超市/便利店"

    return {
        "store": store_text,
        "shopping_list": shopping_list,
        "cook_plan": cook_plan,
        "estimated_budget_cny": "15-30",
        "reason": (
            f"{source_note} 这个方案保留 {top['meal_name']} 的饱腹/蛋白质思路，"
            "适合不想外食时自己快速做一餐。"
        ),
    }


def _build_current_meal_decision(
    top: dict,
    status: dict,
    profile: dict,
    nearby_places: list[dict],
    weather_context: dict | None,
    evidence_rules: dict | None,
    supermarket_value_context: dict | None,
) -> dict:
    meal_type = status["meal_type"]
    meal_type_cn = _meal_type_label(meal_type)
    time_context = status.get("time_context", {})
    walk_minutes = top.get("place_walking_minutes") or _walk_minutes_for(top, nearby_places)
    weather_summary = (weather_context or {}).get("summary", "未提供天气数据")
    health_reasons = _health_explanations(top, status, weather_context, evidence_rules)
    cook_option = _store_purchase_plan(supermarket_value_context, status, top)
    can_cook = profile.get("lifestyle", {}).get("can_cook")
    if can_cook is None:
        can_cook = profile.get("cooking", {}).get("can_cook")
    if can_cook is None:
        can_cook = profile.get("can_cook", True)

    action = "go_to_store_or_restaurant"
    action_reason = "当前综合评分最高的是到店/附近购买方案。"
    if not (nearby_places and _place_source_summary(nearby_places)["is_live"]):
        action = "need_authorized_place_data"
        action_reason = "缺少授权实时地点数据，不能把 fixture 当作真实到店建议。"
    elif can_cook and status.get("want_save_money"):
        action = "buy_ingredients_and_cook"
        action_reason = "你今天有省钱倾向，买菜做饭通常比外食更可控。"

    return {
        "time_based_question": f"今天这个时间点适合吃什么作为{meal_type_cn}？",
        "timezone": time_context.get("timezone", "Asia/Shanghai"),
        "china_time": time_context.get("china_time"),
        "meal_type": meal_type,
        "meal_type_cn": meal_type_cn,
        "recommended_food": top["meal_name"],
        "why_this_food_now": [
            f"现在按中国时间判断是{meal_type_cn}，需要匹配这一餐的饱腹和消化负担。",
            *health_reasons,
            f"天气情境：{weather_summary}",
        ],
        "restaurant_or_takeaway_option": {
            "place": top["place"],
            "food_to_order": top["meal_name"],
            "estimated_price_cny": top["estimated_price_cny"],
            "walk_minutes_from_home": walk_minutes,
            "ordering_keywords": top.get("ordering_keywords") or f"{top['place']} {top['meal_name']}",
            "copyable_note": top.get("copyable_note") or "少油，饮品选无糖。",
            "data_note": "地点来自授权 Provider；价格以实时菜单或到店为准。",
        },
        "buy_ingredients_and_cook_option": cook_option,
        "recommended_action": action,
        "recommended_action_reason": action_reason,
    }


def build_recommendation(
    scored_candidates: list[dict],
    profile: dict,
    status: dict,
    nearby_places: list[dict],
    weather_context: dict | None = None,
    evidence_rules: dict | None = None,
    supermarket_value_context: dict | None = None,
) -> dict:
    top = scored_candidates[0]
    best_value = _pick(scored_candidates, lambda c: "value" in c["tags"] or c["estimated_price_value"] <= 22)
    fat_loss = _pick(scored_candidates, lambda c: "fat_loss" in c["tags"] or "fat_loss_friendly" in c["tags"])
    premium = _pick(scored_candidates, lambda c: c["category"] == "premium")
    budget = _pick(scored_candidates, lambda c: "budget" in c["tags"] or c["estimated_price_value"] <= 20)
    drink = _pick(scored_candidates, lambda c: c["category"] == "drink" and "sweetened" not in c["tags"])
    not_recommended = _pick(scored_candidates[::-1], lambda c: "sweetened" in c["tags"])

    normal_budget = profile["budget_profile"]["normal_meal_budget_cny"]
    current_meal_decision = _build_current_meal_decision(
        top,
        status,
        profile,
        nearby_places,
        weather_context,
        evidence_rules,
        supermarket_value_context,
    )
    result = {
        "user_state_summary": {
            "meal_type": status["meal_type"],
            "today_goal": status["today_goal"],
            "mood": status["mood"],
            "hunger_level": status["hunger_level"],
            "budget_cny": normal_budget,
            "time_context": status.get("time_context", {}),
        },
        "location_summary": {
            "home_address": profile["home_location"]["address"],
            "search_radius_m": profile["home_location"]["search_radius_m"],
            "nearby_place_count": len(nearby_places),
            "selected_walk_minutes": _walk_minutes_for(top, nearby_places),
            "place_data_source": _place_source_summary(nearby_places),
        },
        "weather_context": weather_context
        or {
            "source": "unknown",
            "summary": "未提供天气数据，天气权重按中性处理。",
        },
        "evidence_summary": _evidence_summary(evidence_rules),
        "current_meal_decision": current_meal_decision,
        "restaurant_intelligence": _restaurant_intelligence(nearby_places),
        "supermarket_value_context": supermarket_value_context
        or {
            "summary": "未提供附近超市价格数据，无法判断今天菜价性价比。",
            "good_value_items": [],
        },
        "top_recommendation": {
            "meal_name": top["meal_name"],
            "place": top["place"],
            "total_score": top["total_score"],
            "estimated_price_cny": top["estimated_price_cny"],
            "price_source": top.get("price_source", "local_fixture_or_manual_price"),
            "source_confidence": top.get("source_confidence", "未知"),
            "place_rating": top.get("place_rating"),
            "place_avg_cost_cny": top.get("place_avg_cost_cny"),
            "place_distance_m": top.get("place_distance_m"),
            "place_walking_distance_m": top.get("place_walking_distance_m"),
            "place_walking_minutes": top.get("place_walking_minutes"),
            "place_linear_distance_m": top.get("place_linear_distance_m"),
            "place_signature_dishes": top.get("place_signature_dishes", []),
            "place_menu_data_status": top.get("place_menu_data_status", "unknown"),
            "estimated_calories": top["estimated_calories"],
            "estimated_protein": top["estimated_protein"],
            "satiety_prediction": top["satiety_prediction"],
            "score_components": top["score_components"],
            "reason": top["reason"],
            "health_and_context_reasons": _health_explanations(top, status, weather_context, evidence_rules),
        },
        "best_value_option": _option(best_value),
        "fat_loss_option": _option(fat_loss),
        "premium_option": _option(premium),
        "budget_option": _option(budget),
        "drink_recommendation": {
            "best_drink": drink["meal_name"],
            "avoid_drinks": ["奶茶", "含糖咖啡", "酒精"],
            "reason": "今天目标偏健康和控糖，优先低糖饮品。",
        },
        "not_recommended_today": [
            {
                "name": "炸鸡奶茶套餐",
                "score": 42,
                "reason": "价格不低、热量高、糖分高，今天减脂目标下不优先。",
            },
            {
                "name": not_recommended["meal_name"],
                "score": not_recommended["total_score"],
                "reason": "含糖或满足感偏饮品化，今天不适合作为主推荐。",
            },
        ],
        "shopping_or_ordering_action": {
            "shopping_list": current_meal_decision["buy_ingredients_and_cook_option"]["shopping_list"],
            "cook_plan": current_meal_decision["buy_ingredients_and_cook_option"]["cook_plan"],
            "restaurant_or_takeaway_option": current_meal_decision["restaurant_or_takeaway_option"],
            "recommended_action": current_meal_decision["recommended_action"],
            "ordering_keywords": top.get("ordering_keywords") or "饭团 茶叶蛋 无糖豆浆",
            "copyable_note": top.get("copyable_note") or "饮品选无糖，主食正常量或略少。",
        },
        "safety_note": SAFETY_NOTE,
    }
    return result


def format_chinese_summary(result: dict) -> str:
    top = result["top_recommendation"]
    decision = result.get("current_meal_decision", {})
    note = result["shopping_or_ordering_action"]["copyable_note"]
    not_recommended = "、".join(item["name"] for item in result["not_recommended_today"])
    meal_type = result["user_state_summary"]["meal_type"]
    meal_type_cn = _meal_type_label(meal_type)
    weather = result.get("weather_context", {}).get("summary", "未提供天气数据")
    supermarket_value = result.get("supermarket_value_context", {})
    health_reasons = "\n".join(f"- {reason}" for reason in top.get("health_and_context_reasons", []))
    price_source_cn = {
        "amap_menu_field": "高德返回的菜单字段",
        "amap_avg_cost_estimate": "高德人均消费估算",
        "amap_poi_no_menu_price": "高德 POI 未返回单品价格",
        "local_fixture_or_manual_price": "本地价格数据",
    }.get(top.get("price_source"), top.get("price_source", "未知来源"))
    walk_minutes = result.get("location_summary", {}).get("selected_walk_minutes")
    walk_text = f"距离住处约步行：{walk_minutes} 分钟\n" if walk_minutes is not None else ""
    supermarket_walk = supermarket_value.get("walk_minutes_from_home")
    supermarket_walk_text = (
        f"，离住处约步行 {supermarket_walk} 分钟"
        if supermarket_walk is not None
        else ""
    )
    supermarket_text = (
        f"附近超市：{supermarket_value.get('summary', '未提供超市价格数据')}{supermarket_walk_text}\n"
    )
    return (
        f"今天这个时间点适合吃：{decision.get('recommended_food', top['meal_name'])}\n"
        f"自动判断餐次：{meal_type_cn}\n\n"
        f"去哪里：{top['place']}\n"
        f"推荐分：{top['total_score']}/100\n"
        f"预计价格：{top['estimated_price_cny']}\n"
        f"店铺评分：{top.get('place_rating') or '未知'}\n"
        f"招牌菜参考：{'、'.join(top.get('place_signature_dishes') or []) or '高德未返回'}\n\n"
        f"价格来源：{price_source_cn}\n"
        f"{supermarket_text}"
        f"天气情境：{weather}\n"
        f"{walk_text}\n"
        f"适合原因：\n{top['reason']}\n\n"
        f"身体和情境理由：\n{health_reasons}\n\n"
        f"买菜做饭方案：\n"
        f"去 {decision.get('buy_ingredients_and_cook_option', {}).get('store', '附近超市/便利店')}，"
        f"买 {'、'.join(decision.get('buy_ingredients_and_cook_option', {}).get('shopping_list', []))}，"
        f"做 {decision.get('buy_ingredients_and_cook_option', {}).get('cook_plan', '一份均衡简餐')}。\n\n"
        f"点餐备注：\n{note}\n\n"
        f"今天不推荐：\n{not_recommended}。\n\n"
        f"安全提醒：\n{result['safety_note']}"
    )
