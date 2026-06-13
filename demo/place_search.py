from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

try:
    from .cache_manager import request_json_with_cache
except ImportError:
    from cache_manager import request_json_with_cache


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class PlaceProvider(Protocol):
    source_name: str

    def search(self, profile: dict) -> list[dict]:
        ...


class JsonPlaceProvider:
    source_name = "json_file"

    def __init__(self, places_path: Path):
        self.places_path = places_path

    def search(self, profile: dict) -> list[dict]:
        radius = profile["home_location"]["search_radius_m"]
        max_walk_minutes = profile["lifestyle"].get("max_walk_time_minutes", 12)
        max_walk_distance = max_walk_minutes * 80
        limit = min(radius, max_walk_distance)
        places = load_json(self.places_path)
        return sorted(
            [place for place in places if place["distance_m"] <= limit],
            key=lambda place: place["distance_m"],
        )


class MockPlaceProvider(JsonPlaceProvider):
    source_name = "mock_fixture"

    def __init__(self, places_path: Path | None = None):
        super().__init__(places_path or ROOT / "data" / "mock_nearby_places.json")


class UserProvidedPlaceProvider(JsonPlaceProvider):
    source_name = "user_provided_file"


class AmapPlaceProvider:
    source_name = "authorized_map_api"
    geocode_url = "https://restapi.amap.com/v3/geocode/geo"
    place_around_url = "https://restapi.amap.com/v3/place/around"
    place_detail_url = "https://restapi.amap.com/v3/place/detail"
    walking_route_url = "https://restapi.amap.com/v3/direction/walking"
    food_related_types = "050000|060000"

    def __init__(self, api_key: str, timeout_seconds: float = 8):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def search(self, profile: dict) -> list[dict]:
        location = self._resolve_home_location(profile)
        radius = profile["home_location"]["search_radius_m"]
        data = self._request_json(
            self.place_around_url,
            {
                "key": self.api_key,
                "location": location,
                "radius": radius,
                "types": self.food_related_types,
                "sortrule": "distance",
                "offset": 25,
                "page": 1,
                "extensions": "all",
                "output": "JSON",
            },
        )
        self._ensure_success(data, "Amap place around search failed")
        places = self._normalize_pois(data.get("pois", []), require_distance=True)
        places = self._enrich_places_with_details(places)
        return self._enrich_places_with_walking_routes(location, places)

    def fetch_detail(self, place_id: str) -> dict:
        data = self._request_json(
            self.place_detail_url,
            {
                "key": self.api_key,
                "id": place_id,
                "extensions": "all",
                "output": "JSON",
            },
        )
        self._ensure_success(data, "Amap place detail search failed")
        pois = data.get("pois") or []
        return pois[0] if pois else {}

    def fetch_walking_route(self, origin: str, destination: str) -> dict:
        data = self._request_json(
            self.walking_route_url,
            {
                "key": self.api_key,
                "origin": origin,
                "destination": destination,
                "output": "JSON",
            },
        )
        self._ensure_success(data, "Amap walking route query failed")
        paths = (data.get("route") or {}).get("paths") or []
        return paths[0] if paths else {}

    def _resolve_home_location(self, profile: dict) -> str:
        home = profile["home_location"]
        trust_profile_coordinates = os.getenv("MEALMIND_TRUST_PROFILE_COORDINATES") == "1"
        force_geocode = os.getenv("MEALMIND_FORCE_GEOCODE") == "1"
        if trust_profile_coordinates and not force_geocode and home.get("longitude") and home.get("latitude"):
            return f"{home['longitude']},{home['latitude']}"

        params = {
            "key": self.api_key,
            "address": home["address"],
            "output": "JSON",
        }
        city = home.get("city") or os.getenv("MEALMIND_CITY")
        if city:
            params["city"] = city

        data = self._request_json(self.geocode_url, params)
        self._ensure_success(data, "Amap geocode failed")
        geocodes = data.get("geocodes") or []
        if not geocodes:
            raise ValueError(f"Amap geocode returned no result for address: {home['address']}")
        return geocodes[0]["location"]

    def _request_json(self, url: str, params: dict) -> dict:
        return request_json_with_cache(
            url,
            params,
            timeout_seconds=self.timeout_seconds,
            cache_namespace="amap_place",
        )

    def _ensure_success(self, data: dict, message: str) -> None:
        if data.get("status") != "1":
            info = data.get("info") or data.get("infocode") or "unknown error"
            raise RuntimeError(f"{message}: {info}")

    def _normalize_pois(self, pois: list[dict], require_distance: bool = True) -> list[dict]:
        normalized = []
        for poi in pois:
            category = _classify_amap_poi(poi)
            if category not in {"restaurant", "supermarket", "convenience_store", "drink_shop"}:
                continue
            distance = _safe_int(poi.get("distance"))
            menu_items = _detect_menu_items(poi)
            normalized.append(
                {
                    "place_id": poi.get("id") or poi.get("name"),
                    "name": poi.get("name", ""),
                    "type": category,
                    "distance_m": distance,
                    "rating": _extract_amap_rating(poi),
                    "avg_cost_cny": _extract_amap_cost(poi),
                    "signature_dishes": _extract_signature_dishes(poi),
                    "photos": _extract_amap_photos(poi),
                    "website": poi.get("website") if isinstance(poi.get("website"), str) else "",
                    "address": poi.get("address") if isinstance(poi.get("address"), str) else "",
                    "tel": poi.get("tel") if isinstance(poi.get("tel"), str) else "",
                    "location": poi.get("location") if isinstance(poi.get("location"), str) else "",
                    "typecode": poi.get("typecode", ""),
                    "menu_items": menu_items,
                    "menu_data_status": "menu_price_found" if menu_items else "amap_poi_no_full_menu",
                    "source": self.source_name,
                }
            )
        return sorted(
            [place for place in normalized if not require_distance or place["distance_m"] is not None],
            key=lambda place: place["distance_m"] if place["distance_m"] is not None else 10**9,
        )

    def _enrich_places_with_details(self, places: list[dict]) -> list[dict]:
        detail_limit = _safe_int(os.getenv("MEALMIND_AMAP_DETAIL_LIMIT")) or 0
        if detail_limit <= 0:
            return places

        enriched = []
        for index, place in enumerate(places):
            if index >= detail_limit:
                enriched.append(place)
                continue
            detail = self.fetch_detail(str(place["place_id"]))
            if not detail:
                enriched.append(place)
                continue
            detail_places = self._normalize_pois([detail], require_distance=False)
            if not detail_places:
                enriched.append(place)
                continue
            detail_place = detail_places[0]
            merged = {**place, **detail_place}
            if detail_place.get("distance_m") is None:
                merged["distance_m"] = place.get("distance_m")
            enriched.append(merged)
        return sorted(enriched, key=lambda place: place["distance_m"] or 0)

    def _enrich_places_with_walking_routes(self, origin: str, places: list[dict]) -> list[dict]:
        route_limit = _safe_int(os.getenv("MEALMIND_AMAP_ROUTE_LIMIT"))
        if route_limit is None:
            route_limit = 8
        if route_limit <= 0:
            return places

        enriched = []
        for index, place in enumerate(places):
            if index >= route_limit or not place.get("location"):
                enriched.append(place)
                continue
            try:
                route = self.fetch_walking_route(origin, place["location"])
            except RuntimeError as error:
                place = dict(place)
                place["walking_route_status"] = f"unavailable: {error}"
                enriched.append(place)
                continue
            distance = _safe_int(route.get("distance"))
            duration = _safe_int(route.get("duration"))
            if distance is not None:
                place = dict(place)
                place["amap_linear_distance_m"] = place.get("distance_m")
                place["walking_distance_m"] = distance
                place["walking_minutes"] = round((duration or distance / 80) / 60)
                place["distance_m"] = distance
            enriched.append(place)
        return sorted(enriched, key=lambda place: place["distance_m"] or 0)


class MapApiPlaceProvider(AmapPlaceProvider):
    pass


def provider_from_environment() -> PlaceProvider:
    user_places_path = os.getenv("MEALMIND_NEARBY_PLACES_PATH")
    if user_places_path:
        return UserProvidedPlaceProvider(Path(user_places_path))
    amap_key = os.getenv("AMAP_WEB_SERVICE_KEY") or os.getenv("AMAP_KEY")
    if amap_key:
        return AmapPlaceProvider(amap_key)
    return MockPlaceProvider()


def search_nearby_places(profile: dict, provider: PlaceProvider | None = None) -> list[dict]:
    provider = provider or provider_from_environment()
    return provider.search(profile)


def _safe_int(value) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _extract_amap_rating(poi: dict) -> float | None:
    biz_ext = poi.get("biz_ext")
    if not isinstance(biz_ext, dict):
        return None
    rating = biz_ext.get("rating")
    try:
        return float(rating)
    except (TypeError, ValueError):
        return None


def _extract_amap_cost(poi: dict) -> float | None:
    biz_ext = poi.get("biz_ext")
    if not isinstance(biz_ext, dict):
        return None
    cost = biz_ext.get("cost")
    try:
        return float(cost)
    except (TypeError, ValueError):
        return None


def _extract_signature_dishes(poi: dict) -> list[str]:
    tag = poi.get("tag")
    if not isinstance(tag, str) or not tag.strip():
        return []
    normalized = tag.replace("，", ",").replace("、", ",").replace("；", ",").replace(";", ",")
    return [dish.strip() for dish in normalized.split(",") if dish.strip()]


def _extract_amap_photos(poi: dict) -> list[dict]:
    photos = poi.get("photos")
    if not isinstance(photos, list):
        return []
    normalized = []
    for photo in photos[:5]:
        if not isinstance(photo, dict):
            continue
        url = photo.get("url")
        if not isinstance(url, str) or not url:
            continue
        normalized.append(
            {
                "title": photo.get("title") if isinstance(photo.get("title"), str) else "",
                "url": url,
            }
        )
    return normalized


def _detect_menu_items(payload) -> list[dict]:
    candidates = []
    _collect_menu_like_items(payload, candidates)
    normalized = []
    for item in candidates:
        name = item.get("name") or item.get("dish_name") or item.get("title")
        price = item.get("price") or item.get("price_cny") or item.get("amount")
        if not isinstance(name, str) or not name.strip():
            continue
        normalized.append(
            {
                "name": name.strip(),
                "price_cny": _safe_float(price),
                "source_field": item.get("_source_field", "unknown"),
            }
        )
    return normalized


def _collect_menu_like_items(value, candidates: list[dict], source_field: str = "") -> None:
    menu_keywords = {"menu", "menus", "food", "foods", "dish", "dishes", "meals", "菜品", "菜单"}
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).lower()
            if isinstance(child, list) and any(keyword in key_text for keyword in menu_keywords):
                for item in child:
                    if isinstance(item, dict):
                        copied = dict(item)
                        copied["_source_field"] = str(key)
                        candidates.append(copied)
            _collect_menu_like_items(child, candidates, str(key))
    elif isinstance(value, list):
        for item in value:
            _collect_menu_like_items(item, candidates, source_field)


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _classify_amap_poi(poi: dict) -> str:
    name = poi.get("name", "")
    poi_type = poi.get("type", "")
    typecode = poi.get("typecode", "")
    text = f"{name} {poi_type}"

    if typecode.startswith("0507") or any(
        keyword in text for keyword in ["咖啡", "奶茶", "饮品", "茶饮", "冷饮", "甜品", "古茗", "蜜雪", "茶百道"]
    ):
        return "drink_shop"
    if any(keyword in text for keyword in ["便利店", "全家", "罗森", "7-ELEVEN", "711"]):
        return "convenience_store"
    if any(keyword in text for keyword in ["超市", "生鲜", "菜场", "农贸"]):
        return "supermarket"
    if typecode.startswith("05") or any(keyword in text for keyword in ["餐饮", "饭", "面", "食堂"]):
        return "restaurant"
    return "other"
