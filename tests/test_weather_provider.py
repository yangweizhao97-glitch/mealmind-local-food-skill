from demo.weather_provider import AmapWeatherProvider, provider_from_environment


def test_provider_from_environment_uses_amap_weather_when_key_exists(monkeypatch):
    monkeypatch.setenv("AMAP_WEB_SERVICE_KEY", "fake-key")

    provider = provider_from_environment()

    assert isinstance(provider, AmapWeatherProvider)


def test_amap_weather_provider_normalizes_live_weather(monkeypatch):
    provider = AmapWeatherProvider("fake-key")
    calls = []

    def fake_request(url, params):
        calls.append((url, params))
        if "geocode" in url:
            return {
                "status": "1",
                "geocodes": [{"adcode": "330106"}],
            }
        return {
            "status": "1",
            "lives": [
                {
                    "province": "浙江",
                    "city": "西湖区",
                    "adcode": "330106",
                    "weather": "小雨",
                    "temperature": "12",
                    "winddirection": "东北",
                    "windpower": "≤3",
                    "humidity": "86",
                    "reporttime": "2026-06-13 12:30:00",
                }
            ],
        }

    monkeypatch.setattr(provider, "_request_json", fake_request)

    result = provider.current_weather(
        {"home_location": {"address": "杭州市西湖区某高校公寓", "city": "杭州市"}}
    )

    assert calls[0][1]["address"] == "杭州市西湖区某高校公寓"
    assert calls[1][1]["city"] == "330106"
    assert result["source"] == "authorized_amap_weather"
    assert result["condition"] == "小雨"
    assert result["temperature_c"] == 12
    assert result["humidity"] == 86
    assert "rain_reduce_walking" in result["meal_impact"]
    assert "cold_prefer_hot_meal" in result["meal_impact"]
