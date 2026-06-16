# MealMind 本地饮食决策 Skill

![MealMind README 封面图](assets/mealmind-hero.png)

MealMind 是一个可迁移的“今天吃什么”决策 Skill。它把用户画像、当天身体状态、预算、附近餐馆/超市/便利店、天气、步行距离和循证饮食规则放进同一个评分模型里，输出这一顿具体吃什么、喝什么、去哪买、大概多少钱、为什么这么选。

它不是泛泛地说“吃健康一点”，也不会把某个固定地址附近的店铺写死进仓库。真实推荐必须来自授权地图 API、用户本地配置或用户主动上传的数据；缺少实时 POI 时，demo 会明确停止，而不是编造店铺。

## 适合解决什么问题

- 下课、下班或加班前快速决定一顿饭。
- 在“想省钱、想减脂、不想饿、不想走远、天气不好”之间做取舍。
- 用固定规则把附近餐饮、超市情报和个人偏好转成可执行推荐。
- 作为 Codex Skill / Automation 的本地生活类项目样例。

## 核心能力

- 自动读取中国时间（Asia/Shanghai），推断早餐、午餐、加餐、晚餐或夜间加餐。
- 支持高德 Web 服务 API 查询地理编码、周边 POI、天气和步行路线。
- 只基于授权 POI 或用户上传来源生成餐食候选，不使用假店铺兜底。
- 读取餐馆评分、人均、招牌菜、照片、网址和潜在菜单字段。
- 分析附近超市/便利店是否返回活动或单品价格；没有返回时明确说明。
- 根据目标、营养、价格、距离、天气、心情、口味和数据可信度计算 0-100 分。
- 输出合法 JSON，并生成中文可读推荐总结。
- 提供每天 09:00 和 17:00 运行的 Codex Automation 规划。

## 推荐结果包含

- 今天这个时间点适合吃什么，以及为什么适合当前餐次
- 可以去哪家店吃/买，点什么，预计多少钱，步行多久
- 可以去超市/便利店买什么菜，做成什么饭
- 今日最佳综合推荐
- 附近超市今日菜价/便利店情报
- 性价比最高推荐
- 减脂优先推荐
- 想吃点好的推荐
- 省钱推荐
- 饮品推荐
- 今天不推荐项
- 地图、距离、天气理由
- 点餐关键词和可复制备注
- 依据摘要和安全提醒

核心 JSON 字段是 `current_meal_decision`。它面向直接消费结果的调用方，稳定返回：

- `recommended_food`：此刻建议吃的食物。
- `why_this_food_now`：时间、餐次、天气、距离、身体状态和知识库依据。
- `restaurant_or_takeaway_option`：到店/外带执行方案。
- `buy_ingredients_and_cook_option`：买菜做饭执行方案。
- `recommended_action`：当前优先动作。如果缺少授权地点数据，会返回 `need_authorized_place_data`，不会伪造真实店铺。

## 快速开始

克隆后进入项目目录：

```bash
cd mealmind-local-food-skill
```

安装测试依赖后运行测试：

```bash
python3 -m pytest
```

如果要运行真实地图 demo，需要先设置高德 Web 服务 Key 和本地用户画像路径：

```bash
export AMAP_WEB_SERVICE_KEY="你的高德Web服务Key"
export MEALMIND_FORCE_GEOCODE=1
export MEALMIND_USER_PROFILE_PATH="/path/to/local_user_profile.json"
export MEALMIND_TODAY_STATUS_PATH="/path/to/local_today_status.json"

python3 demo/demo.py
```

运行成功后会同时打印 JSON，并写入默认文件：

```txt
outputs/latest_meal_decision.json
```

也可以指定输出路径：

```bash
export MEALMIND_OUTPUT_JSON_PATH="/path/to/meal_decision.json"
python3 demo/demo.py
```

没有 Key 或授权 POI 时，demo 会提示缺少实时餐馆/超市 POI 情报，不会回退到示例餐馆。

## 数据 Provider 设计

这个 Skill 的可复用边界是 Provider，而不是某个固定地址附近的 JSON 文件。

- `profiles/user_profile.json`：匿名示例用户画像。真实用户信息建议复制到本地私有文件，并用 `MEALMIND_USER_PROFILE_PATH` 指定。
- `data/today_status.json`：当天心情、饥饿程度、压力、能量、睡眠、运动和目标等动态状态。
- `demo/place_search.py`：地点查询 Provider。设置 `AMAP_WEB_SERVICE_KEY` 或 `AMAP_KEY` 后使用高德 Web 服务实时查询附近 POI；也可以通过 `MEALMIND_NEARBY_PLACES_PATH` 接入用户授权导出的地点文件。
- `demo/weather_provider.py`：使用同一个高德 Key 查询天气，并转成吃饭影响标签。
- `demo/supermarket_value.py`：分析附近超市/便利店是否有活动或单品价。
- `demo/meal_candidate_generator.py`：根据 Provider 返回的店名、人均、评分、招牌菜和菜单字段生成候选餐。

地图 API 能实时查附近有什么店、距离多远、地址、评分、人均和部分 POI 信息。如果没有返回完整菜单、今日菜价或活动，MealMind 会明确说明，不会用示例菜单补结果。

## 实时地图查询

当前实现接入高德 Web 服务 API。运行时默认优先使用用户画像里的住址做高德地理编码，避免旧经纬度导致定位漂移。随后调用周边搜索 API 查询搜索半径内的餐饮、购物类 POI，并标准化为 `restaurant`、`supermarket`、`convenience_store`、`drink_shop` 等类型。

如果你确信 profile 里的经纬度比住址地理编码更准，可以显式启用：

```bash
export MEALMIND_TRUST_PROFILE_COORDINATES=1
```

周边搜索返回的距离可能是直线或近似距离。当前实现默认对前 8 个 POI 调用高德步行路径规划，并用真实步行距离/时间覆盖评分距离：

```bash
export MEALMIND_AMAP_ROUTE_LIMIT=8
```

如果 Key 次数很紧，可以设为 `3` 或 `0`。

想强制使用用户自己导出的地点文件，可以设置：

```bash
export MEALMIND_NEARBY_PLACES_PATH="/path/to/nearby_places.json"
```

## 高德字段探测

高德 App 商家页里展示的完整菜单，不一定会通过开放平台 Web 服务 API 返回。当前代码会尽量读取开放 API 里可能出现的餐饮信息：

- `tag`：美食类 POI 的特色菜/招牌菜。
- `biz_ext.rating`：评分。
- `biz_ext.cost`：人均消费。
- `photos`：店铺照片。
- `website`：店铺网址。
- `menu` / `foods` / `dishes` 等可能出现的菜单字段。

拿到 Key 后，建议先运行一次探针：

```bash
export AMAP_WEB_SERVICE_KEY="你的高德Web服务Key"
export MEALMIND_FORCE_GEOCODE=1
python3 demo/amap_probe.py
```

如果想对前 1 家店额外调用 ID 详情接口：

```bash
export MEALMIND_AMAP_DETAIL_LIMIT=1
python3 demo/amap_probe.py
```

## 请求缓存

高德地理编码、周边 POI、POI 详情、步行路线和天气请求默认缓存 30 分钟，缓存文件写入 `cache/`，不会保存 API Key。

```bash
export MEALMIND_CACHE_TTL_SECONDS=1800
```

临时禁用缓存：

```bash
export MEALMIND_DISABLE_CACHE=1
```

## 评分模型

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

评分维度会同时考虑饮食目标、营养结构、预算、步行距离、天气适配、心情和身体状态、口味偏好，以及数据来源可信度。

## 仓库结构

```txt
mealmind-local-food-skill/
├── README.md
├── SKILL.md
├── AGENTS.md
├── automation_prompt.md
├── assets/
├── agents/
├── profiles/
├── data/
├── demo/
├── schemas/
├── docs/
└── tests/
```

## 进一步文档

- [设计说明](docs/design.md)
- [评分模型](docs/scoring_model.md)
- [实时上下文设计](docs/live_context_design.md)
- [数据源规划](docs/data_source_plan.md)
- [自动化规划](docs/automation_plan.md)
- [安全策略](docs/safety_policy.md)

## 后续规划

- 接入更多地图 Provider，例如百度地图或腾讯位置服务。
- 接入公开优惠和用户授权上传的价格截图。
- 增加 OCR 菜单识别。
- 后续接入 Apple Health / Apple Watch。
- 把 Codex Automation 接入真实每日提醒流程。

## 安全免责声明

MealMind 是日常饮食建议工具，不是医疗产品，不提供医疗诊断。如有疾病、孕期、进食障碍风险、正在服药或特殊饮食限制，请咨询医生或专业营养师。

## 项目介绍话术

MealMind 是一个本地饮食决策 Skill。用户提前填写个人信息表，系统根据固定住址加载附近饭店、便利店、超市、饮品店和咖啡店信息，再结合每天输入的心情、饥饿程度、压力、能量、睡眠、工作强度、是否运动、天气和今日目标，生成具体饮食推荐。

它会输出吃什么、喝什么、去哪里买、大概多少钱、为什么推荐、今天不建议吃什么，以及点餐关键词。第一版先把“真实数据来源 + 稳定评分方法 + 可解释推荐”做扎实，再逐步接入更多个人健康数据和自动化提醒。
