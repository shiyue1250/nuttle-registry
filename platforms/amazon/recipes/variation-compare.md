# Amazon 变体对比

人打开几个候选商品的详情页，Agent 把每个商品的颜色变体、可售状态汇成一张对比表，指出变体覆盖的差异。
价格不在这份数据里（见「已知边界」），这份配方回答的是"谁的变体更全、哪些颜色断货"。

## 需要

- 平台包 `amazon`（映射卡 `amazon/dp-twister` ≥ 0.2.0，实体类型 `variation`）
- 控制台「采集范围」里 Amazon 平台开着
- 人在 amazon.com 打开商品详情页（`/dp/<ASIN>`），页面内嵌的变体数据会被采到，不需要点任何东西

## 变体实体的字段

`id（变体 ASIN）, label（颜色名）, state（SELECTED / AVAILABLE / UNAVAILABLE …）, page_path（来自哪个页面，形如 /dp/<父 ASIN>/_dom/a-state:…）, extra.hidden`

父商品 ASIN 从 `page_path` 里取：`/dp/` 后面的 10 位。

## Agent 提示模板

```
你通过囤囤鼠的 MCP 工具读取我在 amazon.com 上打开过的商品页里的变体数据，做变体对比。数据只来自我已经打开的页面，不要尝试抓取。

流程：
1. 调用 query_entities(platform="amazon", kind="variation", limit=500)。
2. 按 page_path 里的父 ASIN 分组（正则 /dp/([A-Z0-9]{10})）。每组一个商品。
3. 对每个商品统计：变体总数、可售（state 为 AVAILABLE 或 SELECTED）数、不可售数、颜色名列表。
4. 输出一张对比表：父 ASIN | 变体数 | 可售 | 不可售 | 颜色。然后指出：
   - 哪个商品变体覆盖最全、哪个断货最多
   - 只有某一家有的颜色（用颜色名做集合差）
5. 如果我又打开了新的商品页，我会说"再来"，你重新执行第 1 步；或者调用 wait_for_capture(path_contains="twister-sort-filter", timeout_secs=60) 等我打开下一个。

约束：不要下结论说"哪个更好卖"，这份数据里没有价格和销量；不要修改或删除任何映射。
```

## 已知边界

- `desktop-twister-sort-filter-data` 只有维度信息，没有每个变体的价格和库存数；价格要等变体切换请求被采到后另出一张卡。
- 只覆盖 `color_name` 维度；尺寸只有一个值时不出现在变体里。
- 同一个变体 ASIN 只会有一条实体，多次打开同一商品页是覆盖不是累加。
