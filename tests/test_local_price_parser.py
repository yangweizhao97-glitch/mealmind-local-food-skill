from demo.local_price_parser import parse_local_price_text


def test_parse_local_price_text_extracts_items():
    text = """楼下惠民超市今日特价：
鸡胸肉 12.8/斤
鸡蛋 9.9/10个
西兰花 5.9/斤
香蕉 3.9/斤
玉米 2.5/根
无糖豆浆 3.5/瓶"""

    parsed = parse_local_price_text(text)

    assert parsed["store_name"] == "楼下惠民超市"
    assert len(parsed["items"]) == 6
    assert parsed["items"][0]["price_cny"] == 12.8
    assert "protein" in parsed["items"][0]["tags"]
