# 小红书评论洞察

人翻笔记评论，Agent 边收边聚合，输出每篇笔记的主题、情绪、追问点，并把值得深挖的评论打上「待核实」交给人确认。
桥只做桥：这份配方是给 Agent 的提示模板，分析在 Agent 里做，不在桥里做。

## 需要

- 平台包 `xiaohongshu`（映射卡 `xiaohongshu/note`、`xiaohongshu/comment-page`、`xiaohongshu/comment-sub`；实体类型 `note`、`comment`）
- 控制台「插件」页小红书为「已启用」；有用的接口是 `/api/sns/web/v1/feed`（笔记）、`/api/sns/web/v2/comment/page`（评论）、`/api/sns/web/v2/comment/sub/page`（展开的回复）
- 人打开小红书网页版，进笔记详情页展开评论、翻页、点「展开回复」（游客只能看到第一页评论，登录后才能翻页）

## 评论实体的字段

`id, note_id, content, like_count（字符串）, create_time（秒）, ip_location, sub_comment_count（字符串）, reply_count, user_id, nickname, head, extra.sub_comments, extra.pictures`；展开的回复另有 `reply_to`（回复的是哪条评论）、`reply_to_nickname`

`like_count` 是字符串，排序前自己转成数字。

## Agent 提示模板

把下面整段作为任务说明给 Agent：

```
你通过囤囤鼠的 MCP 工具读取我在小红书网页版上看过的评论，做评论洞察。数据只来自我已经看过的页面，不要尝试抓取。

流程：
1. 先 list_tags 确认标签集里有「待核实」。
2. 循环：调用 wait_for_capture(path_contains="comment/page", after_id=<上次返回的 cursor>, timeout_secs=60)。
   - 返回 new > 0：调用 query_entities(platform="xiaohongshu", kind="comment", limit=500)，只处理 last_seen 大于本轮开始时间的评论。
   - 返回 timed_out：告诉我"等你翻页"，再等一轮；连续 3 轮没有新评论就结束并输出总结。
3. 每轮把新评论按 note_id 分组，对每篇笔记整理：
   - 主题：评论集中在聊什么（3 条以内，每条一句话，带出现次数）
   - 情绪：正面 / 负面 / 疑问 各占多少条，用 like_count 加权说明哪种声音更受认同
   - 追问点：用户在问但笔记没回答的问题，原样引用评论 content
   - 值得深挖：吐槽、需求、对比竞品的评论，对每条调用
     tag_entity(platform="xiaohongshu", kind="comment", id=<评论 id>, tag="待核实", note="<一句话说明为什么值得看>")
4. 结束时输出：按笔记的总结表 + 本次打了多少条「待核实」+ 提醒我去控制台「数据」页确认，确认后的评论我会改成「需求池」。
5. 之后我说"看需求池"时，调用 query_entities(platform="xiaohongshu", kind="comment", tag="需求池") 并按我的备注（tags[].note）归纳需求方向。

约束：不要给评论打「需求池」或「忽略」，那是我来决定的；不要修改或删除任何映射；引用评论时保留原文，不要改写。
```

## 输出示例（结构）

| 笔记 note_id | 评论数 | 主题 | 情绪 | 追问点 | 待核实 |
|---|---|---|---|---|---|
| 6aa0e3…bbc3 | 23 | 什么时候来澳洲（7）… | 正面 15 / 疑问 6 / 负面 2 | 「有没有 26 寸的」 | 3 |

## 已知边界

- 桥只存人看过的页面；翻到第几页评论就只有到第几页。
- `wait_for_capture` 是长轮询，Agent 调用时才阻塞，桥不会主动推送。
- 一级评论自带的少量子评论在 `extra.sub_comments` 里；点「展开回复」加载的回复单独成实体（同为 `comment`，带 `reply_to`）。要看「笔记 + 评论树」整体，用 get_thread(platform="xiaohongshu", kind="note", id=<笔记 id>)。
