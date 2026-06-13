from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_schema(path: Path | None = None) -> dict:
    path = path or ROOT / "schemas" / "meal_decision_schema.json"
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_meal_decision(output: dict, schema: dict | None = None) -> bool:
    schema = schema or load_schema()
    required = schema.get("required", [])
    missing = [key for key in required if key not in output]
    if missing:
        raise ValueError(f"Missing required output keys: {', '.join(missing)}")

    properties = schema.get("properties", {})
    for key, spec in properties.items():
        if key not in output:
            continue
        expected_type = spec.get("type")
        if expected_type == "object" and not isinstance(output[key], dict):
            raise TypeError(f"{key} must be an object")
        if expected_type == "array" and not isinstance(output[key], list):
            raise TypeError(f"{key} must be an array")
        if expected_type == "string" and not isinstance(output[key], str):
            raise TypeError(f"{key} must be a string")
    return True
