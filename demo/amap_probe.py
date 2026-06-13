from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from .place_search import AmapPlaceProvider, load_json
    from .weather_provider import AmapWeatherProvider
except ImportError:
    from place_search import AmapPlaceProvider, load_json
    from weather_provider import AmapWeatherProvider


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    api_key = os.getenv("AMAP_WEB_SERVICE_KEY") or os.getenv("AMAP_KEY")
    if not api_key:
        raise SystemExit("Set AMAP_WEB_SERVICE_KEY before running this probe.")

    profile_path = os.getenv("MEALMIND_USER_PROFILE_PATH")
    profile = load_json(Path(profile_path).expanduser() if profile_path else ROOT / "profiles" / "user_profile.json")
    place_provider = AmapPlaceProvider(api_key)
    weather_provider = AmapWeatherProvider(api_key)
    places = place_provider.search(profile)
    weather = weather_provider.current_weather(profile)
    sample = places[: int(os.getenv("MEALMIND_PROBE_LIMIT", "5"))]
    print(
        json.dumps(
            {
                "weather": weather,
                "places": sample,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
