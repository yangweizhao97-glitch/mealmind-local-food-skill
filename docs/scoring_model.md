# 评分模型

每个候选餐食打 0-100 分。

```txt
meal_score =
goal_match * 0.20
+ nutrition_structure * 0.16
+ price_value * 0.15
+ distance_convenience * 0.12
+ weather_match * 0.10
+ mood_body_match * 0.12
+ taste_preference * 0.08
+ data_confidence * 0.07
```

## 组件含义

- `goal_match`：是否匹配减脂、省钱、增肌、想吃好点等目标。
- `price_value`：是否在预算内，以及价格是否合理。
- `nutrition_structure`：蛋白质、碳水、蔬菜、低糖饮品是否均衡。
- `distance_convenience`：是否近、快、容易买，是否符合最大步行时间。
- `weather_match`：是否适合雨天、冷天、热天、空气质量等情境。
- `mood_body_match`：是否适合今天的心情、饥饿、压力、工作强度和运动状态。
- `taste_preference`：是否符合喜欢、不喜欢和过敏信息。
- `data_confidence`：地图、价格、天气和营业状态数据是否新鲜可信。
