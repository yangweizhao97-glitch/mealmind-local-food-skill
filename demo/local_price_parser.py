from __future__ import annotations

import re


TAG_RULES = {
    "鸡胸肉": ["protein"],
    "鸡蛋": ["protein"],
    "茶叶蛋": ["protein"],
    "西兰花": ["vegetable"],
    "香蕉": ["fruit", "carb"],
    "玉米": ["carb"],
    "无糖豆浆": ["drink", "low_sugar"],
}


def infer_tags(name: str) -> list[str]:
    for keyword, tags in TAG_RULES.items():
        if keyword in name:
            return tags
    return []


def parse_local_price_text(text: str) -> dict:
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    store_name = "未知小店"
    if lines:
        store_name = re.sub(r"(今日特价|特价|：|:).*", "", lines[0]).strip() or store_name

    items = []
    pattern = re.compile(r"^(?P<name>[\u4e00-\u9fa5A-Za-z0-9]+)\s+(?P<price>\d+(?:\.\d+)?)\s*/\s*(?P<unit>.+)$")
    for line in lines[1:]:
        match = pattern.match(line)
        if not match:
            continue
        name = match.group("name")
        items.append(
            {
                "name": name,
                "price_cny": float(match.group("price")),
                "unit": match.group("unit").strip(),
                "tags": infer_tags(name),
            }
        )

    return {"store_name": store_name, "source_type": "manual_text", "items": items}
