from demo.place_search import AmapPlaceProvider, provider_from_environment


def test_provider_from_environment_uses_amap_when_key_exists(monkeypatch):
    monkeypatch.delenv("MEALMIND_NEARBY_PLACES_PATH", raising=False)
    monkeypatch.setenv("AMAP_WEB_SERVICE_KEY", "fake-key")

    provider = provider_from_environment()

    assert isinstance(provider, AmapPlaceProvider)


def test_amap_provider_geocodes_address_by_default_even_with_profile_coordinates(monkeypatch):
    provider = AmapPlaceProvider("fake-key")
    monkeypatch.delenv("MEALMIND_TRUST_PROFILE_COORDINATES", raising=False)
    monkeypatch.setattr(
        provider,
        "_request_json",
        lambda url, params: {
            "status": "1",
            "geocodes": [{"location": "120.111,30.222"}],
        },
    )

    location = provider._resolve_home_location(
        {
            "home_location": {
                "address": "杭州市西湖区某高校公寓",
                "city": "杭州市",
                "longitude": 1,
                "latitude": 2,
            }
        }
    )

    assert location == "120.111,30.222"


def test_amap_provider_normalizes_food_related_pois():
    provider = AmapPlaceProvider("fake-key")
    pois = [
        {
            "id": "a1",
            "name": "某某兰州牛肉面",
            "type": "餐饮服务;中餐厅",
            "typecode": "050100",
            "distance": "430",
            "address": "示例路1号",
            "website": "https://example.com/menu",
            "tag": "牛肉面,拌面,羊肉串",
            "biz_ext": {"rating": "4.2", "cost": "22"},
            "photos": [{"title": "门头", "url": "https://example.com/photo.jpg"}],
            "foods": [{"name": "牛肉面小份", "price": "18"}],
        },
        {
            "id": "a2",
            "name": "某某生鲜超市",
            "type": "购物服务;超级市场",
            "typecode": "060400",
            "distance": "180",
            "address": "示例路2号",
            "biz_ext": {"rating": "4.0"},
        },
        {
            "id": "a3",
            "name": "某某银行",
            "type": "金融保险服务",
            "typecode": "160000",
            "distance": "120",
        },
    ]

    places = provider._normalize_pois(pois)

    assert [place["name"] for place in places] == ["某某生鲜超市", "某某兰州牛肉面"]
    assert places[0]["type"] == "supermarket"
    assert places[1]["type"] == "restaurant"
    assert places[1]["source"] == "authorized_map_api"
    assert places[1]["avg_cost_cny"] == 22
    assert places[1]["signature_dishes"] == ["牛肉面", "拌面", "羊肉串"]
    assert places[1]["photos"] == [{"title": "门头", "url": "https://example.com/photo.jpg"}]
    assert places[1]["menu_items"] == [
        {"name": "牛肉面小份", "price_cny": 18.0, "source_field": "foods"}
    ]
    assert places[1]["menu_data_status"] == "menu_price_found"


def test_amap_provider_keeps_distance_when_detail_has_no_distance(monkeypatch):
    provider = AmapPlaceProvider("fake-key")
    place = {
        "place_id": "a1",
        "name": "某某兰州牛肉面",
        "type": "restaurant",
        "distance_m": 430,
        "rating": None,
        "source": "authorized_map_api",
    }

    monkeypatch.setenv("MEALMIND_AMAP_DETAIL_LIMIT", "1")
    monkeypatch.setattr(
        provider,
        "fetch_detail",
        lambda place_id: {
            "id": place_id,
            "name": "某某兰州牛肉面",
            "type": "餐饮服务;中餐厅",
            "typecode": "050100",
            "tag": "牛肉面,凉面",
            "biz_ext": {"rating": "4.5", "cost": "20"},
        },
    )

    enriched = provider._enrich_places_with_details([place])

    assert enriched[0]["distance_m"] == 430
    assert enriched[0]["rating"] == 4.5
    assert enriched[0]["avg_cost_cny"] == 20
    assert enriched[0]["signature_dishes"] == ["牛肉面", "凉面"]


def test_amap_provider_classifies_cold_drink_shop():
    provider = AmapPlaceProvider("fake-key")

    places = provider._normalize_pois(
        [
            {
                "id": "d1",
                "name": "古茗",
                "type": "餐饮服务;冷饮店",
                "typecode": "050700",
                "distance": "100",
            }
        ]
    )

    assert places[0]["type"] == "drink_shop"


def test_amap_provider_enriches_places_with_walking_route(monkeypatch):
    provider = AmapPlaceProvider("fake-key")
    monkeypatch.setenv("MEALMIND_AMAP_ROUTE_LIMIT", "1")
    monkeypatch.setattr(
        provider,
        "fetch_walking_route",
        lambda origin, destination: {"distance": "2400", "duration": "1800"},
    )

    places = [
        {
            "place_id": "p1",
            "name": "需要绕路的食堂",
            "type": "restaurant",
            "distance_m": 120,
            "location": "120.1,30.1",
            "source": "authorized_map_api",
        }
    ]

    enriched = provider._enrich_places_with_walking_routes("120.0,30.0", places)

    assert enriched[0]["amap_linear_distance_m"] == 120
    assert enriched[0]["walking_distance_m"] == 2400
    assert enriched[0]["walking_minutes"] == 30
    assert enriched[0]["distance_m"] == 2400


def test_amap_provider_keeps_places_when_walking_route_limit_is_exceeded(monkeypatch):
    provider = AmapPlaceProvider("fake-key")
    monkeypatch.setenv("MEALMIND_AMAP_ROUTE_LIMIT", "1")

    def fail_route(origin, destination):
        raise RuntimeError("Amap walking route query failed: CUQPS_HAS_EXCEEDED_THE_LIMIT")

    monkeypatch.setattr(provider, "fetch_walking_route", fail_route)
    places = [
        {
            "place_id": "p1",
            "name": "路线超限餐馆",
            "type": "restaurant",
            "distance_m": 120,
            "location": "120.1,30.1",
            "source": "authorized_map_api",
        }
    ]

    enriched = provider._enrich_places_with_walking_routes("120.0,30.0", places)

    assert enriched[0]["name"] == "路线超限餐馆"
    assert enriched[0]["distance_m"] == 120
    assert "CUQPS_HAS_EXCEEDED_THE_LIMIT" in enriched[0]["walking_route_status"]
