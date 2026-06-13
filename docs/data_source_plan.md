# 数据来源规划

## MVP

- 固定用户画像：默认 `profiles/user_profile.json` 为匿名示例，真实配置通过 `MEALMIND_USER_PROFILE_PATH` 指向本地私有文件。
- 今日状态：默认 `data/today_status.json` 为示例，真实当天状态通过 `MEALMIND_TODAY_STATUS_PATH` 指向本地私有文件。
- 附近地点：授权地图 Provider，当前实现为高德 Web 服务 API。
- 餐馆情报：高德 POI `rating`、`cost`、`tag`、`photos`、`website` 和可能出现的菜单字段。
- 超市/便利店情报：高德 POI 距离、地址、评分；若未返回活动或单品价格，必须明确标注缺失。
- 用户主动提供的本地菜价文本：仅用于解析器或后续 OCR/手动输入流程，不作为默认推荐依据。
- mock 天气：`data/mock_weather_context.json`
- 循证饮食规则：`data/evidence_rules.json`

## 后续版本

- 地图 API：高德地图、百度地图、腾讯地图。
- 天气 API：地图平台天气、公开天气服务。
- 价格数据：官方接口、公开页面、用户授权截图、OCR、本地手动维护价格库。
- 健康数据：Apple Health / Apple Watch，必须用户授权。

## 禁止项

不要爬取私人微信群。不要未授权爬取饿了么、大众点评、美团。不要自动点餐或付款。

## 数据可信度

- `verified_user_input`：用户亲自确认的住址、过敏、价格、常去店。
- `authorized_api`：地图、天气或官方接口返回。
- `user_uploaded_ocr`：用户授权上传图片后识别。
- `mock`：只能用于测试解析器或离线单元测试，不能生成面向用户的店铺推荐。
- `unknown`：不可作为强依据。
