from demo.supermarket_value import analyze_supermarket_value


def test_analyze_supermarket_value_marks_good_deals():
    food_sources = {
        "supermarket_prices": [
            {
                "place_name": "示例社区生鲜超市",
                "items": [
                    {"name": "鸡胸肉", "price_cny": 12.8, "reference_price_cny": 16.0, "unit": "斤"},
                    {"name": "玉米", "price_cny": 2.5, "reference_price_cny": 3.5, "unit": "根"},
                ],
            }
        ]
    }
    nearby_places = [{"name": "示例社区生鲜超市", "distance_m": 240}]

    result = analyze_supermarket_value(food_sources, None, nearby_places)

    assert result["walk_minutes_from_home"] == 3
    assert [item["name"] for item in result["good_value_items"]] == ["鸡胸肉", "玉米"]
    assert "性价比较高" in result["summary"]
