from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from .cache_manager import request_json_with_cache
except ImportError:
    from cache_manager import request_json_with_cache


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


class MockWeatherProvider:
    source_name = "mock_weather"

    def __init__(self, weather_path: Path | None = None):
        self.weather_path = weather_path or ROOT / "data" / "mock_weather_context.json"

    def current_weather(self, profile: dict) -> dict:
        return load_json(self.weather_path)


class AmapWeatherProvider:
    source_name = "authorized_amap_weather"
    geocode_url = "https://restapi.amap.com/v3/geocode/geo"
    weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"

    def __init__(self, api_key: str, timeout_seconds: float = 8):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def current_weather(self, profile: dict) -> dict:
        adcode = self._resolve_adcode(profile)
        data = self._request_json(
            self.weather_url,
            {
                "key": self.api_key,
                "city": adcode,
                "extensions": "base",
                "output": "JSON",
            },
        )
        self._ensure_success(data, "Amap weather query failed")
        lives = data.get("lives") or []
        if not lives:
            raise ValueError(f"Amap weather returned no live weather for adcode: {adcode}")
        return _normalize_amap_live_weather(lives[0])

    def _resolve_adcode(self, profile: dict) -> str:
        home = profile["home_location"]
        if home.get("adcode"):
            return str(home["adcode"])

        data = self._request_json(
            self.geocode_url,
            {
                "key": self.api_key,
                "address": home["address"],
                "city": home.get("city", ""),
                "output": "JSON",
            },
        )
        self._ensure_success(data, "Amap weather geocode failed")
        geocodes = data.get("geocodes") or []
        if not geocodes:
            raise ValueError(f"Amap geocode returned no adcode for address: {home['address']}")
        adcode = geocodes[0].get("adcode")
        if not adcode:
            raise ValueError(f"Amap geocode result has no adcode for address: {home['address']}")
        return str(adcode)

    def _request_json(self, url: str, params: dict) -> dict:
        return request_json_with_cache(
            url,
            params,
            timeout_seconds=self.timeout_seconds,
            cache_namespace="amap_weather",
        )

    def _ensure_success(self, data: dict, message: str) -> None:
        if data.get("status") != "1":
            info = data.get("info") or data.get("infocode") or "unknown error"
            raise RuntimeError(f"{message}: {info}")


def provider_from_environment() -> MockWeatherProvider | AmapWeatherProvider:
    api_key = os.getenv("AMAP_WEB_SERVICE_KEY") or os.getenv("AMAP_KEY")
    if api_key:
        return AmapWeatherProvider(api_key)
    return MockWeatherProvider()


def get_weather_context(profile: dict, provider=None) -> dict:
    provider = provider or provider_from_environment()
    return provider.current_weather(profile)


def _normalize_amap_live_weather(live: dict) -> dict:
    weather = live.get("weather", "")
    temperature = _safe_int(live.get("temperature"))
    wind_level = _parse_wind_level(live.get("windpower"))
    meal_impact = _meal_impacts(weather, temperature, wind_level)
    return {
        "source": "authorized_amap_weather",
        "data_freshness": "live",
        "province": live.get("province", ""),
        "city": live.get("city", ""),
        "adcode": live.get("adcode", ""),
        "condition": weather,
        "temperature_c": temperature,
        "wind_direction": live.get("winddirection", ""),
        "wind_level": wind_level,
        "humidity": _safe_int(live.get("humidity")),
        "report_time": live.get("reporttime", ""),
        "meal_impact": meal_impact,
        "summary": _weather_summary(weather, temperature, wind_level),
    }


def _meal_impacts(weather: str, temperature: int | None, wind_level: int | None) -> list[str]:
    impacts = []
    if any(keyword in weather for keyword in ["雨", "雪", "冻雨", "冰雹"]):
        impacts.append("rain_reduce_walking")
    if wind_level is not None and wind_level >= 5:
        impacts.append("wind_reduce_walking")
    if temperature is not None and temperature <= 14:
        impacts.append("cold_prefer_hot_meal")
    if temperature is not None and temperature >= 28:
        impacts.append("hot_prefer_light_meal")
    impacts.append("avoid_iced_drinks_at_dinner")
    return impacts


def _weather_summary(weather: str, temperature: int | None, wind_level: int | None) -> str:
    temp_text = f"{temperature}℃" if temperature is not None else "温度未知"
    wind_text = f"，风力约 {wind_level} 级" if wind_level is not None else ""
    if weather:
        return f"{weather}，{temp_text}{wind_text}，本餐按实时天气调整距离和冷热偏好。"
    return f"{temp_text}{wind_text}，本餐按实时天气调整距离和冷热偏好。"


def _safe_int(value) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_wind_level(value) -> int | None:
    if value is None:
        return None
    text = str(value)
    digits = "".join(char for char in text if char.isdigit())
    if not digits:
        return None
    return int(digits[0])
