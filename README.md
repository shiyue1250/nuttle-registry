# DataBridge registry — 映射市场

映射卡是纯数据：告诉桥「某个接口的响应里，哪些字段是什么」。不含代码，不发请求，只作用于用户自己已经采到的数据。

```
schema/mapping-card.schema.json      映射卡的 JSON Schema
platforms/<平台>/platform.json       域名、建议关注的接口、噪音接口、采集提示
platforms/<平台>/mappings/<卡>.json          映射卡
platforms/<平台>/mappings/<卡>.fixture.json  脱敏样本 + 期望产出，CI 和本机都用它校验
```

桥的 exe 编译时把这个目录打进去，首次启动从内置包种入平台和卡，离线可用。
「检查更新」只从这个仓库读文件，**只下不上**，不上传任何采集数据。

## 校验一张卡

```bash
databridge --check registry/platforms/xiaohongshu/mappings/comment-page.json           # 跑样本，比对期望产出
databridge --check registry/platforms/xiaohongshu/mappings/comment-page.json --update  # 把当前产出写回样本的 expected
```

退出码 0 = 通过。样本文件格式：`{"response": <脱敏后的原始响应>, "expected": [<实体>...]}`。

## 配方（recipes/）

每个平台包下的 `recipes/*.md` 是给 Agent 的提示模板：用哪个包、哪张卡、怎么循环 `wait_for_capture`、输出什么，
以及哪些判断留给人（打标签）。分析在 Agent 里做，桥不碰。Agent 用 MCP `list_recipes` / `get_recipe` 取到全文；
控制台「映射市场」页也能看。首批两份：`xiaohongshu/comment-insight`（评论洞察）、`amazon/variation-compare`（变体对比）。

## 源路径能写什么

- 点号路径取嵌套值：`user_info.nickname`；数组下标用数字：`images.0.url`
- 末尾 `/N` 做除法：`price/100`（分转元）、`rate/10000`
- `$path` / `$host` 取请求上下文：响应正文之外唯一能引用的东西，比如 Amazon 变体要记来自哪个商品页
- 目标字段以 `extra.` 开头的整块保留原值（嵌套列表照搬）

样本文件可带 `"context": {"host": …, "path": …}`，校验 `$path` / `$host` 时用。

## 发布一张卡

1. 在桥里把映射调通（Agent 用 `add_mapping`，或控制台）。
2. 控制台接口行点「导出卡」，或 MCP `export_mapping(pattern, platform, entity)`：得到 `卡.json` + `卡.fixture.json`，样本已按下面的规则脱敏。
3. 把两个文件放进 `platforms/<平台>/mappings/`，本地跑 `databridge --check` 和 `python scripts/build_index.py`，提 PR。

CI（`.github/workflows/check.yml`）做三件事：卡符合 Schema、`index.json` 与目录一致、用桥的 exe 跑样本。
第三步依赖仓库变量 `DATABRIDGE_CHECK_URL`（指向 `databridge.exe` 的下载地址），未设置时跳过。

桥在运行时也给每张卡记账：命中次数、产出条数；命中了但连续 3 次一条都提不出来标 `stale`，控制台接口行显示「卡可能失效」，`list_mappings` 里能看到。发现失效请在这里提 issue 或 PR 附新样本，桥不会自动上报。

## 脱敏

样本从真实响应截取。数字、布尔、`id` 类字段保留（校验靠它们）；`user_id / nickname / xsec_token / image` 换成同值同占位的假值；正文类字符串截到 20 字。
