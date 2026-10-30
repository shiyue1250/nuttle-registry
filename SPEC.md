# Nuttle Mapping Card Spec v1

[中文版见下方](#中文)

A **mapping card** turns one JSON API response that a web page already loaded into a list of structured entities that an AI agent can query. A **platform pack** groups the cards, endpoint labels and agent recipes for one website.

## Principles (normative)

Every card and pack conforming to this spec is:

1. **Passive** — it only describes data the user's own browser has already received while the user browsed normally. Cards never trigger, schedule or paginate requests.
2. **Read-only** — cards never modify requests or responses and never replay them.
3. **Credential-free** — cards and fixtures must not contain cookies, tokens, `Authorization` headers, signatures or account identifiers of the author.
4. **Pure data** — no code of any kind (no JavaScript, WASM, regex callbacks, templates that execute). A host may evaluate only the field-path DSL below.
5. **Local** — the extracted entities stay on the user's machine. Nothing in this spec requires or permits uploading captured data.

A host that cannot guarantee these properties for a card must refuse to install it.

## Card format

JSON, one file per card, validated by [`schema/mapping-card.schema.json`](schema/mapping-card.schema.json).

| Field | Required | Meaning |
| --- | --- | --- |
| `apiVersion` | recommended | Spec version, must be `1`. Omitted means `1` (cards published before v1). Hosts reject any other value |
| `id` | yes | `<pack id>/<card name>`, lowercase `[a-z0-9-]` |
| `version` | yes | Semantic version of the card |
| `platform` | yes | The pack id this card belongs to |
| `entity` | yes | Entity type produced, e.g. `comment`, `product`, `variation` |
| `match.host` | no | Substring of the response host |
| `match.path` | yes | Substring of the response path (query string excluded). A `*` matches any run of characters, so the pieces must appear in order (e.g. `/video/*/_dom/__INITIAL_STATE__`); hosts older than 2026-10-29 read `*` literally and never match such a card |
| `item_path` | yes | Dot path from the response root to the array of items; empty string if the response itself is the array. If the path resolves to a single object, it is treated as one item. A `*` segment walks every value of an object or array (e.g. `note.noteDetailMap.*.note`, where the keys are ids) |
| `fields` | yes | Output field → source path. Must contain `id` (used to de-duplicate) |
| `fixture` | to publish | Sibling file `<name>.fixture.json` with `response` (redacted) and `expected` (entities) |
| `locales` | no | `{ "zh": {name, description}, "en": {name, description} }` |
| `jsonld` | no | `{ "@type": "<schema.org type>", "map": { field: schemaProperty } }` for JSON-LD output |
| `schema`, `trigger`, `pagination`, `noise`, `note`, `author`, `license`, `verified` | no | Documentation for humans and agents |
| `display` | no | Table layout for hosts: `columns` (ordered output fields to show) and `labels` (`{zh:{field:label}, en:{…}}`). `schema.<field>.type` (`unix_s`, `int`, `image`, `duration_s`) tells the host how to render a value |
| `relations` | no | Parent/child structure for hosts: `parent` `{card, field, count_field}` (this entity's `field` equals the parent card entity's `id`; `count_field` on the parent holds the platform's total), `reply_to` (field naming the entity this one replies to; `"0"`/empty = top level), `replies` (field holding inline replies) and `reply_fields` (output field → source path for each inline reply, same DSL) |
| `resource` | no | `{plugin, match: {resourceField: entityField}}` — the plugin resource (downloadable media) that corresponds to an entity |

### Field-path DSL

- `a.b.c` — walk object keys; numeric segments index arrays.
- `path/N` — divide the number at `path` by `N`, rounded to 2 decimals (e.g. `create_time/1000` turns milliseconds into seconds).
- `extra.<name>` as an **output** field keeps the whole source value under `extra`.
- `$path` / `$host` as a **source** read the request context instead of the response body; `$q.<name>` reads a query parameter of the request URL (raw, not decoded).
- `=<template>` as a **source** builds a string, mainly the original link: `=https://{$host}/dp/{defaultAsin}`. Braces hold a field path or a `$` variable. If any placeholder is empty the whole value is null — never a half-built link.

An item whose direct fields (everything except `id`, `=` templates and `$` context) all come out null is skipped. Lists often mix in other kinds of items (e.g. "people also search" blocks among search results) that carry an `id`, sometimes enough to fill a link template, but none of the card's own fields; they never become entities.

Nothing else. The DSL is intentionally not Turing-complete.

### Fixture and verification

`nuttle --check <card.json>...` runs the host's real extraction engine on the fixture's `response` and compares the result with `expected`. Exit code `0` means every card matches. A card without a fixture cannot be published.

Redaction is the author's responsibility: besides the author's own account data, replace third-party content (comment text, locations, real platform ids that identify a person) with placeholders in both `response` and `expected`.

## Platform pack format

A directory (or a repository) with:

```text
platform.json          # validated by schema/platform.schema.json
mappings/<name>.json   # cards
mappings/<name>.fixture.json
recipes/<name>.md      # optional agent prompt templates; first line is the title
recipes/<name>.en.md   # optional English version of the same recipe (falls back to <name>.md)
```

`platform.json` fields: `apiVersion` (1), `id`, `version`, `label`, `locales`, `hosts` (`*.` prefix matches subdomains), and optional `endpoints` (`[{match, label}]` — what each API endpoint is for), `watches`, `noise`, `notes`, `homepage`.

Optional `connector`: brand parameters for a built-in protocol connector, so a new brand on a known protocol ships as a pack, not an app release. `kind` picks the connector: `folder` (local folders the user picks, no parameters; pack `files`) or `imap`: `providers` lists mail services (`id`, `name`, address `domains` used to auto-pick the service, `host`, `port`, `help` shown next to the credential field, `secret_label` naming that field) plus default `folders`, and `classify`: ordered mail rules (`category` personal / notification / subscription / ad, matched on `subject` / `from` substrings, `precedence` values, and `list` / `auto` / `answered` / `own` flags; the first rule whose conditions all hold wins, otherwise personal). One pack (`mail`) holds every service and the user adds as many accounts as they like; adding a service is a pack update. The connector logs in with the user's own credential (kept in the OS keychain, never in the pack), reads only, and hands raw data to `/nuttle/<id>/*` for this pack's cards to parse. A pack with `hosts: []` and a `connector` is fed only by the connector.

## Parts recipes

`parts/<id>.json`, validated by [`schema/parts-recipe.schema.json`](schema/parts-recipe.schema.json): how to break **one** captured item into parts (steps, parameters, judgments; later shots), each pointing back to where it came from (paragraph number plus a verbatim quote). Fields: `apiVersion` (1), `id`, `version`, `name` (`{zh, en}`), `on.media` (`text` / `video` / `image`), `input` (`text`, later `ocr` / `frames` / `transcript`, prepared by the host), `types` (`{<type>: {name, cols: [{id, zh, en}]}}`; the first column is the part's main text) and `prompt` (`{zh, en}`). The host numbers the text by paragraph, sends it with the prompt to the user's own model (or hands it to the user's AI over MCP `start_parts` / `submit_parts`), keeps a part only if its type is declared and its quote is found verbatim, and never lets a re-run overwrite a part the person edited. The host ships `points` (steps / parameters / judgments of any text); industry packs will add their own (e.g. a short-drama shot list).

## Publishing

### Official packs

Live in this repository under `platforms/`. Changes go through pull requests and CI (`check.yml`): schema validation, fixture replay, index consistency.

### Community packs (decentralized)

Publish from **your own public repository**; no pull request to this repository is needed.

```bash
nuttle card new my-pack my-pack "*.example.com" "Example"   # scaffold a pack repository
nuttle card lint my-pack                                     # static checks before release
nuttle card replay my-pack                                   # run every card against its fixture
```

1. One repository = one pack, with `platform.json` at the repository root.
2. Add the GitHub topic **`nuttle-pack`**.
3. Every card and `platform.json` declare `apiVersion: 1`; every card has a fixture.
4. Create a **non-draft, non-prerelease GitHub Release** whose tag equals `platform.json.version` (an optional `v` prefix is allowed), e.g. tag `v1.2.0` for version `1.2.0`. Never move an existing tag.
5. The pack `id` must not equal any official pack id.

`discover.yml` runs daily: it searches the topic, applies the rules above, and writes accepted packs to `index.json` under `community`. Files are served from jsDelivr at the release tag (`https://cdn.jsdelivr.net/gh/<owner>/<repo>@<tag>/…`). The topic means you opted in; it is **not** a security review. Nuttle shows community packs with a "Community" badge, their repository, domains and cards, and asks the user to confirm before installing.

## Versioning of this spec

Breaking changes bump `apiVersion`. Hosts must reject cards with an `apiVersion` they do not support rather than guess.

---

<a id="中文"></a>

# Nuttle 映射卡规范 v1

**映射卡**把网页本来就加载了的一个 JSON 接口响应，变成 AI Agent 能查询的结构化实体列表。**平台包**把一个网站的映射卡、接口用途标注和 Agent 配方打包在一起。

## 原则（强制）

所有符合本规范的卡和包都必须是：

1. **被动的**：只描述用户正常浏览时自己浏览器已经收到的数据。卡永远不会触发、定时或翻页发请求。
2. **只读的**：不修改请求或响应，也不重放请求。
3. **不含凭证**：卡和样本里不能有 Cookie、token、`Authorization`、签名或作者的账号标识。
4. **纯数据**：不含任何代码（没有 JavaScript、WASM、正则回调、可执行模板），宿主只解释下面的字段路径语法。
5. **本地的**：提取出的实体留在用户本机。本规范不要求、也不允许上传采集到的数据。

宿主无法为某张卡保证以上性质时，必须拒绝安装。

## 卡的格式

每张卡一个 JSON 文件，按 [`schema/mapping-card.schema.json`](schema/mapping-card.schema.json) 校验。字段含义见英文版表格，要点：

- `apiVersion` 必须是 `1`；不写视为 `1`（兼容 v1 之前发布的卡）；其他值一律拒绝。
- `id` 写成 `<包 id>/<卡名>`；`fields` 必须包含 `id`，用于去重。
- `item_path` 指向条目数组；如果指向的是单个对象，按一条处理（例如一次只上报一个视频的接口）。路径里的 `*` 段取对象（或数组）的每个值，用于以 id 为键的对象，例如 `note.noteDetailMap.*.note`。
- `display`（可选）：给宿主的表格布局——`columns` 是要显示的字段及顺序，`labels` 是中英文列名；`schema.<字段>.type`（`unix_s` / `int` / `image` / `duration_s`）决定怎么显示。
- `relations`（可选）：父子结构——`parent` 写明挂在哪张卡的实体下（本实体的 `field` 等于父实体的 `id`，父实体的 `count_field` 是平台上的总数）；`reply_to` 是「回复给谁」的字段（`"0"` 或空为一级）；`replies` 是内嵌回复所在字段，`reply_fields` 说明内嵌回复怎么读（同一套路径语法）。宿主据此组装「视频 + 评论树」。
- `resource`（可选）：这张卡的实体对应哪个插件的哪条可下载资源，`match` 写资源字段 → 实体字段。
- `locales` 提供中英文名称和说明；`jsonld` 声明产出实体对应的 schema.org 类型和字段对应关系。

### 字段路径语法

- `a.b.c`：按键逐层取值，数字段表示数组下标。
- `路径/N`：把取到的数除以 N，保留两位小数，例如 `create_time/1000` 把毫秒换成秒。
- 输出字段写成 `extra.<名>`：把源值整块保留到 `extra` 里。
- 源路径写 `$path` / `$host`：取请求上下文，而不是响应正文；`$q.<名>` 取请求网址的查询参数（原样，不解码）。
- 源路径以 `=` 开头是模板，主要用来拼原文链接：`=https://{$host}/dp/{defaultAsin}`。花括号里是字段路径或 `$` 变量，任一处为空则整条为空，不产出半截链接。

仅此而已，这套语法刻意不具备图灵完备性。

### 样本与校验

`nuttle --check <卡.json>...` 用宿主真实的提取引擎跑样本里的 `response`，与 `expected` 比对，退出码 `0` 表示全部一致。没有样本的卡不能发布。

脱敏由作者负责：除了自己的账号信息，第三方内容（评论正文、地域、能定位到个人的真实平台 id）也要在 `response` 和 `expected` 中同步换成占位。

## 平台包格式

一个目录（或一个仓库），包含 `platform.json`、`mappings/` 下的卡与样本、可选的 `recipes/` 配方（第一行是标题；同名加 `.en.md` 是英文版，没有英文版时按中文版给）。`platform.json` 字段：`apiVersion`（1）、`id`、`version`、`label`、`locales`、`hosts`（`*.` 前缀匹配所有子域），可选 `endpoints`（`[{match, label}]`，每个接口是做什么的）、`watches`、`noise`、`notes`、`homepage`。可选 `connector`：内置协议连接器的品牌参数，同协议的新品牌只发包、不发版。`kind` 选连接器：`folder`（用户选的本机文件夹，没有参数；包 `files`）或 `imap`：`providers` 列各家邮箱服务商（`id`、`name`、用来按地址自动认服务商的后缀 `domains`、`host`、`port`、填凭据处显示的 `help`、凭据那一栏的名字 `secret_label`），外加默认 `folders`；`classify` 是邮件分类规则（`category` 取 personal / notification / subscription / ad，条件有主题 / 发件地址含某段文字 `subject` / `from`、`precedence` 取值、`list` / `auto` / `answered` / `own` 四个开关；从上往下第一条全满足的生效，都不满足是 personal）。所有服务商都在一个包（`mail`）里，用户可添加多个账户；加服务商只更新包。连接器用用户自己的凭据（存系统凭据管理器，不进包）只读取数，交回 `/nuttle/<id>/*` 由本包的卡解析。

## 拆解配方

`parts/<id>.json`，按 [`schema/parts-recipe.schema.json`](schema/parts-recipe.schema.json) 校验：把**一条**采集内容拆成零件（步骤、参数、判断，以后还有镜头），每块带出处（段号 + 原话）。字段：`apiVersion`（1）、`id`、`version`、`name`（`{zh, en}`）、`on.media`（`text` / `video` / `image`）、`input`（`text`，以后 `ocr` / `frames` / `transcript`，由宿主准备）、`types`（`{类型: {name, cols: [{id, zh, en}]}}`，第一列是零件的主文字）、`prompt`（`{zh, en}`）。宿主把原文按段编号，连同提示交给用户自己的模型（或经 MCP `start_parts` / `submit_parts` 交给用户的 AI），类型不在配方里、原话在原文里找不到的丢弃；重拆不覆盖人改过的。宿主自带 `points`（任意文字的步骤 / 参数 / 判断）；行业包以后带自己的（如短剧镜头表）。

## 发布

**官方包**放在本仓库 `platforms/` 下，走 PR 和 CI（Schema 校验、样本回放、索引一致性）。

**社区包（去中心化）**在你**自己的公开仓库**发布，不需要向本仓库提 PR。命令行工具：`nuttle card new <目录> <包id> <域名> [显示名]` 生成仓库骨架，`nuttle card lint <目录>` 做发布前静态检查，`nuttle card replay <目录>` 用样本回放每张卡。

1. 一个仓库一个包，`platform.json` 放在仓库根目录；
2. 给仓库加上 GitHub 标签 **`nuttle-pack`**；
3. `platform.json` 和每张卡都写 `apiVersion: 1`，每张卡都有样本；
4. 创建**正式的 GitHub Release**（不是草稿、不是预发布），标签等于 `platform.json.version`，可带 `v` 前缀，例如版本 `1.2.0` 用标签 `v1.2.0`。不要移动已有标签；
5. 包 id 不能和官方包重名。

`discover.yml` 每天运行一次：搜索这个标签，按上面的规则校验，把合格的包写进 `index.json` 的 `community`。文件从 jsDelivr 上该 Release 标签的地址下载。**打标签只代表作者主动加入，不代表经过安全审核。** Nuttle 会给社区包标上「社区」，展示来源仓库、域名和卡，安装前要用户确认。

## 规范版本

有不兼容的改动时提升 `apiVersion`。宿主遇到不支持的 `apiVersion` 必须拒绝，不能猜。
