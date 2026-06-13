# MealMind 本地饮食决策 Skill

MealMind 是一个可迁移的本地饮食决策 Skill。用户只需要提供自己的住址、预算、饮食偏好和当天状态；附近饭店、超市、便利店、饮品店、菜单价格和天气应由可替换的数据 Provider 查询或由用户授权上传。它会推荐今天这一顿吃什么、喝什么、去哪买、大概多少钱、离住处多远，以及为什么这么选。

## MVP 功能

- 读取固定用户画像。
- 使用 Provider 接口读取附近饭店、便利店、超市、饮品店和咖啡店；没有授权 POI 情报时不生成示例店铺推荐。
- 读取当天状态。
- 查询中国时间（Asia/Shanghai），自动把当前餐次修正为早餐、午餐、加餐、晚餐或夜间加餐。
- 设置高德 Key 后读取高德实时天气；无 Key 时只保留 mock 天气测试能力。
- 读取循证饮食规则知识库。
- 读取高德 POI 的评分、人均、招牌菜、照片、网址和潜在菜单字段。
- 分析附近超市/便利店是否有活动或单品价格返回；没有返回时明确说明。
- 只基于实时 POI 或授权来源生成餐食候选。
- 使用固定评分模型打分，综合目标、营养、价格、距离、天气、心情、口味和数据可信度。
- 输出合法 JSON 和中文推荐总结。
- 提供 Codex Automation 每天 09:00 和 17:00 的运行计划。

## 为什么有用

日常吃饭决策经常卡在“想省钱、想减脂、又不想饿、还懒得走太远”这些冲突里。MealMind 把用户偏好、附近食物、预算、天气、距离、心情和当天状态放进同一个评分模型，输出具体可执行的选择。

## 系统如何工作

1. `profiles/user_profile.json` 保存匿名示例用户信息；真实用户信息建议放在本地私有文件中，并用环境变量指定。
2. `data/` 保存 mock 天气、循证规则和用户画像示例；不要把某个用户真实附近店铺长期写死在这里。
3. `demo/time_context.py` 读取中国时间并推断当前餐次，同时按餐次修正天气文案。
4. `demo/place_search.py` 根据距离筛选附近地点。
5. `demo/weather_provider.py` 通过高德天气 API 查询当前天气，并转成吃饭影响标签。
6. `demo/local_price_parser.py` 可解析用户主动提供的菜价文本，但默认推荐不依赖示例菜单。
7. `demo/meal_candidate_generator.py` 只根据授权 POI 返回的店名、人均、评分、招牌菜和菜单字段生成候选餐食。
8. `demo/meal_scorer.py` 基于目标、营养、价格、距离、天气、心情、口味和数据可信度计算 0-100 分。
9. `demo/recommendation_engine.py` 选择最佳、性价比、减脂、高级、省钱和饮品推荐。
10. `demo/validate_output.py` 校验输出结构。

## 数据 Provider 设计

这个 Skill 的可复用边界是 Provider，而不是某个固定地址附近的 JSON 文件。

- `profiles/user_profile.json`：只保存匿名示例用户画像和住址。别人拿走时可以复制成自己的本地配置文件，或用 `MEALMIND_USER_PROFILE_PATH` 指定私有配置。
- `demo/place_search.py`：定义地点查询 Provider。设置 `AMAP_WEB_SERVICE_KEY` 或 `AMAP_KEY` 后会使用高德 Web 服务实时查询附近 POI；也可以通过 `MEALMIND_NEARBY_PLACES_PATH` 接入用户授权导出的地点文件。
- `demo/weather_provider.py`：设置同一个高德 Key 后调用高德天气查询 API，通过住址地理编码得到 adcode，再查询实况天气。
- `demo/supermarket_value.py`：根据实时 POI 输出附近超市/便利店情报；高德未返回活动或单品价时明确标注。
- `demo/meal_candidate_generator.py`：根据 Provider 返回的店名、人均、评分、招牌菜、菜单字段生成候选餐，不硬编码某个小区或学校周边店名。

## 实时地图查询

当前实现接入高德 Web 服务 API：

1. 申请高德开放平台 Web 服务 API Key。
2. 在终端设置环境变量：

```bash
export AMAP_WEB_SERVICE_KEY="你的高德Web服务Key"
export MEALMIND_USER_PROFILE_PATH="/path/to/local_user_profile.json"
export MEALMIND_TODAY_STATUS_PATH="/path/to/local_today_status.json"
```

3. 运行 demo：

```bash
python3 demo/demo.py
```

运行时默认优先使用用户画像里的住址做高德地理编码，避免旧经纬度导致定位漂移。默认读取 `profiles/user_profile.json`，也可以用 `MEALMIND_USER_PROFILE_PATH` 指向本地私有文件。随后调用高德周边搜索 API 查询搜索半径内的餐饮、购物类 POI，并把返回结果标准化为 `restaurant`、`supermarket`、`convenience_store`、`drink_shop` 等类型。没有实时 POI 时不会生成推荐。

如果你确信 profile 里的经纬度比住址地理编码更准，可以显式启用：

```bash
export MEALMIND_TRUST_PROFILE_COORDINATES=1
```

周边搜索返回的距离可能是直线/近似距离。为避免校园围墙、校区入口、道路绕行导致误判，当前实现会默认对前 8 个 POI 调用高德步行路径规划，并用真实步行距离/时间覆盖评分距离。

控制步行路线查询数量：

```bash
export MEALMIND_AMAP_ROUTE_LIMIT=8
```

如果 Key 次数很紧，可以先设为 `3` 或 `0`。

兼容旧配置，也可以强制按住址重新地理编码：

```bash
export MEALMIND_FORCE_GEOCODE=1
```

如果想强制使用用户自己导出的地点文件，可以设置：

```bash
export MEALMIND_NEARBY_PLACES_PATH="/path/to/nearby_places.json"
```

注意：地图 API 能实时查“附近有什么店、距离多远、地址、评分、人均、招牌菜等 POI 信息”。如果未返回完整菜单、今日菜价或活动，本 Skill 会明确说明，不会用示例菜单补结果。

### 高德餐饮字段探测

高德 App 商家页里展示的完整菜单，不一定会通过开放平台 Web 服务 API 返回。当前代码会尽量读取开放 API 里可能出现的餐饮信息：

- `tag`：美食类 POI 的特色菜/招牌菜。
- `biz_ext.rating`：评分。
- `biz_ext.cost`：人均消费。
- `photos`：店铺照片。
- `website`：店铺网址。
- `menu` / `foods` / `dishes` 等可能出现的菜单字段；如果真实返回中存在，会自动提取菜名和价格。

拿到 Key 后，建议先运行一次探针：

```bash
export AMAP_WEB_SERVICE_KEY="你的高德Web服务Key"
export MEALMIND_FORCE_GEOCODE=1
python3 demo/amap_probe.py
```

探针会查询实时天气和周边 POI。默认 POI 只做周边搜索。如果想对前 1 家店额外调用 ID 详情接口：

```bash
export MEALMIND_AMAP_DETAIL_LIMIT=1
python3 demo/amap_probe.py
```

`MEALMIND_AMAP_DETAIL_LIMIT` 会增加额外请求次数。Key 次数有限时，建议先设为 `1`。

### 请求缓存

高德地理编码、周边 POI、POI 详情、步行路线和天气请求默认缓存 30 分钟，缓存文件写入 `cache/`，不会保存 API Key。

调整缓存时间：

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

## 仓库结构

```txt
mealmind-local-food-skill/
├── README.md
├── SKILL.md
├── AGENTS.md
├── automation_prompt.md
├── agents/
├── profiles/
├── data/
├── demo/
├── schemas/
├── docs/
└── tests/
```

## 如何运行 demo

先设置高德 Web 服务 Key：

```bash
export AMAP_WEB_SERVICE_KEY="你的高德Web服务Key"
export MEALMIND_FORCE_GEOCODE=1
export MEALMIND_USER_PROFILE_PATH="/path/to/local_user_profile.json"
```

再运行：

```bash
python3 demo/demo.py
```

没有 Key 时，demo 会提示缺少实时 POI，不会回退到示例餐馆。

## 如何测试

```bash
python3 -m pytest
```

## 后续规划

- 接入高德地图、百度地图或腾讯地图。
- 接入天气 API，把降雨、温度、空气质量写入今日动态情报区。
- 接入公开优惠和用户授权上传的价格截图。
- 增加 OCR 菜单识别。
- 后续接入 Apple Health / Apple Watch。
- 把 Codex Automation 接入真实每日提醒流程。

## 安全免责声明

MealMind 是日常饮食建议工具，不是医疗产品，不提供医疗诊断。如有疾病、孕期、进食障碍风险、正在服药或特殊饮食限制，请咨询医生或专业营养师。

## 二面项目介绍话术

MealMind 是一个本地饮食决策 Skill。第一版不接 Apple Watch 或 HealthKit，而是先做一个更实际的 MVP：用户提前填写个人信息表，系统根据固定住址加载附近饭店、便利店、超市、饮品店和咖啡店信息，再结合用户每天输入的心情、饥饿程度、压力、能量、睡眠、工作强度、是否运动、天气和今日目标，生成具体饮食推荐。

它不会只说“吃健康一点”，而是输出吃什么、喝什么、去哪里买、大概多少钱、为什么推荐、今天不建议吃什么，以及点餐关键词。
