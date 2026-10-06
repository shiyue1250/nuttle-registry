# Nuttle 囤囤鼠 registry — 映射市场

映射卡是纯数据：告诉桥「某个接口的响应里，哪些字段是什么」。不含代码，不发请求，只作用于用户自己已经采到的数据。

**规范全文：[SPEC.md](SPEC.md)（映射卡规范 v1，中英双语）。** 想发布自己的平台包，不需要给这个仓库提 PR：
在你自己的公开仓库放好 `platform.json` 和卡，加上 GitHub 标签 `nuttle-pack`，发一个标签等于版本号的正式 Release，
每天的自动发现会把它收进索引，在囤囤鼠里以「社区」包出现。规则见 SPEC.md「发布」一节。

```
SPEC.md                              映射卡规范 v1
schema/mapping-card.schema.json      映射卡的 JSON Schema
schema/platform.schema.json          平台包的 JSON Schema
scripts/build_index.py               生成索引；--discover 同时发现社区包（scripts/discover.py）
.github/workflows/discover.yml       每天自动发现社区包
platforms/<平台>/platform.json       域名、建议关注的接口、噪音接口、接口用途标注（endpoints: [{match, label}]）、采集提示
platforms/<平台>/mappings/<卡>.json          映射卡
platforms/<平台>/mappings/<卡>.fixture.json  脱敏样本 + 期望产出，CI 和本机都用它校验
```

桥的 exe 编译时把这个目录打进去，首次启动从内置包种入平台和卡，离线可用。
「检查更新」只从这个仓库读文件，**只下不上**，不上传任何采集数据。

## Claude Code 插件

本仓库同时是一个 Claude Code 插件市场：

```bash
claude plugin marketplace add shiyue1250/databridge-registry
claude plugin install nuttle@nuttle
```

插件 `claude-plugin/` 做两件事：自动接入本机囤囤鼠的 MCP（`http://127.0.0.1:8787/mcp`）；带一个 `write-card` 技能，
让 Agent 从「你浏览过的网站」一路走到「卡发布为社区包」——找接口、看结构、登记并核对、导出脱敏样本、`card lint` / `card replay`，
**创建公开仓库和发 Release 之前一定先征得你的同意**。

## 社区包的命令行工具

```bash
nuttle card new my-pack my-pack "*.example.com" "示例站"   # 生成社区平台包仓库骨架
nuttle card lint my-pack                                   # 发布前静态检查（错误必须修，提示可选）
nuttle card replay my-pack                                 # 用样本回放每张卡，等同 --check
```

`lint` 按社区包的标准检查：`apiVersion` 必须写明、包 id 不能与官方包重名、每张卡都有样本、样本里疑似凭证的关键词会提示。

## 校验一张卡

```bash
nuttle --check registry/platforms/xiaohongshu/mappings/comment-page.json           # 跑样本，比对期望产出
nuttle --check registry/platforms/xiaohongshu/mappings/comment-page.json --update  # 把当前产出写回样本的 expected
```

退出码 0 = 通过。样本文件格式：`{"response": <脱敏后的原始响应>, "expected": [<实体>...]}`。

## 配方（recipes/）

每个平台包下的 `recipes/*.md` 是给 Agent 的提示模板：用哪个包、哪张卡、怎么循环 `wait_for_capture`、输出什么，
以及哪些判断留给人（打标签）。分析在 Agent 里做，桥不碰。Agent 用 MCP `list_recipes` / `get_recipe` 取到全文；
控制台「市场」里每个平台包卡片上能看到；在卡片上点「装到 Claude Code」即装成技能 `/nuttle-<平台>-<配方名>`；它们同时是 MCP 提示（同名），其他 Agent 客户端也能调用。首批两份：`xiaohongshu/comment-insight`（评论洞察）、`amazon/variation-compare`（变体对比）。

英文版放同目录、同名加 `.en`：`comment-insight.en.md`。`build_index.py` 把它挂到配方条目的 `locales.en {title, path}`，
不会当成独立配方；装包时一并下载。英文界面复制、Agent 用 `get_recipe(lang="en")` 取到的就是英文版，没有英文版就给中文。

## 源路径能写什么

- 点号路径取嵌套值：`user_info.nickname`；数组下标用数字：`images.0.url`
- 末尾 `/N` 做除法：`price/100`（分转元）、`rate/10000`
- `$path` / `$host` 取请求上下文：比如 Amazon 变体要记来自哪个商品页；`$q.<名>` 取请求网址里的查询参数（原样不解码）
- 以 `=` 开头是模板，用来拼原文链接：`"url": "=https://{$host}/dp/{defaultAsin}"`，花括号里写点号路径或 `$` 变量；任一处取不到值就整条为空，不产出坏链接
- 目标字段以 `extra.` 开头的整块保留原值（嵌套列表照搬）

样本文件可带 `"context": {"host": …, "path": …, "q": {…}}`，校验 `$path` / `$host` / `$q` 时用。导出样本时查询参数的值一律换成 `EXAMPLE`。

**每张卡尽量带 `url`（原文链接）**：用户要能从数据回到原帖。平台网页上打不开的（例如视频号）就不写，别拼打不开的链接。

## 发布一张卡

1. 在桥里把映射调通（Agent 用 `add_mapping`，或控制台）。
2. 控制台接口行点「导出卡」，或 MCP `export_mapping(pattern, platform, entity)`：得到 `卡.json` + `卡.fixture.json`，样本已按下面的规则脱敏。
3. 把两个文件放进 `platforms/<平台>/mappings/`，本地跑 `nuttle --check` 和 `python scripts/build_index.py`，提 PR。

CI（`.github/workflows/check.yml`）做三件事：卡符合 Schema、`index.json` 与目录一致、用桥的 exe 跑样本。
第三步依赖仓库变量 `NUTTLE_CHECK_URL`（指向 `nuttle.exe` 的下载地址），未设置时跳过。

桥在运行时也给每张卡记账：命中次数、产出条数；命中了但连续 3 次一条都提不出来标 `stale`，控制台接口行显示「卡可能失效」，`list_mappings` 里能看到。发现失效请在这里提 issue 或 PR 附新样本，桥不会自动上报。

## 脱敏

样本从真实响应截取。数字、布尔、`id` 类字段保留（校验靠它们）；`user_id / nickname / xsec_token / image` 换成同值同占位的假值；正文类字符串截到 20 字。
