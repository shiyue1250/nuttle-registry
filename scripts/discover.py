"""发现社区平台包：搜索打了 nuttle-pack 标签的 GitHub 仓库，校验后生成索引的 community 部分。

收录条件（照 res-downloader 扩展商店的做法）：
  1. 仓库公开、未归档、不是 fork，带 TOPIC 标签；一个仓库一个平台包，platform.json 在仓库根目录
  2. 有正式 Release（GitHub 的 releases/latest 本身就排除草稿和预发布）
  3. Release 标签去掉可选的 v 前缀后，必须等于 platform.json 的 version
  4. platform.json 与每张卡都写 apiVersion: 1；包 id 不能与官方包重名；卡的 id 必须以「包 id/」开头且带样本
不满足就跳过这个仓库并打印原因，不影响其他仓库。整个过程只有 GET，不上传任何东西。

文件下载走 jsDelivr 上该仓库对应 tag 的地址（国内也能访问），即索引条目里的 base。
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

TOPIC = "nuttle-pack"   # 改名前叫 nuttle-pack，当时还没有社区包，不必兼容
API = "https://api.github.com"
ID_RE = re.compile(r"^[a-z0-9-]+$")


class Skip(Exception):
    """这个仓库不收录，附原因"""


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "databridge-registry"})
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith(API):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def http_json(url: str):
    return json.loads(_get(url))


def http_text(url: str) -> str:
    return _get(url).decode("utf-8")


def search_repos(gh) -> list:
    repos, page = [], 1
    while page <= 10:
        res = gh(f"{API}/search/repositories?q=topic:{TOPIC}+archived:false+fork:false&sort=updated&per_page=100&page={page}")
        repos += res.get("items", [])
        if len(res.get("items", [])) < 100:
            break
        page += 1
    return repos


def _listing(gh, full: str, sub: str, tag: str) -> list:
    try:
        return gh(f"{API}/repos/{full}/contents/{sub}?ref={tag}")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise


def inspect(repo: dict, official_ids: set, gh, raw) -> dict:
    full = repo["full_name"]
    if repo.get("fork") or repo.get("archived") or repo.get("private"):
        raise Skip("fork / 已归档 / 私有")
    try:
        rel = gh(f"{API}/repos/{full}/releases/latest")
    except urllib.error.HTTPError as e:
        raise Skip(f"没有正式 Release（{e.code}）") from e
    tag = rel["tag_name"]
    version = tag[1:] if tag.startswith("v") else tag
    raw_base = f"https://raw.githubusercontent.com/{full}/{tag}"
    try:
        plat = json.loads(raw(f"{raw_base}/platform.json"))
    except Exception as e:  # noqa: BLE001
        raise Skip(f"仓库根目录没有可读的 platform.json：{e}") from e
    pid = plat.get("id", "")
    if plat.get("apiVersion") != 1:
        raise Skip(f"platform.json 的 apiVersion 必须是 1，现在是 {plat.get('apiVersion')!r}")
    if not ID_RE.match(pid):
        raise Skip(f"包 id 不合法：{pid!r}")
    if pid in official_ids:
        raise Skip(f"包 id 与官方包重名：{pid}")
    if plat.get("version") != version:
        raise Skip(f"Release 标签 {tag} 与 platform.json 的 version {plat.get('version')} 不一致")
    if not plat.get("hosts"):
        raise Skip("platform.json 没有 hosts")

    files = {f["name"] for f in _listing(gh, full, "mappings", tag)}
    cards = []
    for name in sorted(n for n in files if n.endswith(".json") and not n.endswith(".fixture.json")):
        card = json.loads(raw(f"{raw_base}/mappings/{name}"))
        cid = card.get("id", "")
        if card.get("apiVersion") != 1:
            raise Skip(f"卡 {name} 的 apiVersion 必须是 1")
        if card.get("platform") != pid or not cid.startswith(f"{pid}/"):
            raise Skip(f"卡 {name} 的 id / platform 必须属于包 {pid}")
        for k in ("version", "entity", "match", "item_path", "fields"):
            if k not in card:
                raise Skip(f"卡 {name} 缺少 {k}")
        if card.get("fixture") not in files:
            raise Skip(f"卡 {name} 没有对应的样本文件")
        cards.append({"id": cid, "version": card["version"], "entity": card["entity"],
                      "verified": card.get("verified"), "fixture": True, "path": f"mappings/{name}"})

    recipes = []
    for f in _listing(gh, full, "recipes", tag):
        if f["name"].endswith(".md"):
            stem = f["name"][:-3]
            first = raw(f"{raw_base}/recipes/{f['name']}").splitlines()[:1]
            recipes.append({"id": f"{pid}/{stem}", "title": (first[0] if first else stem).lstrip("# ").strip(),
                            "path": f"recipes/{f['name']}"})

    return {
        "id": pid, "version": version, "label": plat.get("label", pid), "locales": plat.get("locales"),
        "hosts": plat["hosts"], "cards": cards, "recipes": recipes, "path": "platform.json",
        "base": f"https://cdn.jsdelivr.net/gh/{full}@{tag}",
        "repo": full, "tag": tag, "official": False,
        "author": repo.get("owner", {}).get("login"), "stars": repo.get("stargazers_count", 0),
        "published": rel.get("published_at"),
    }


def discover(official_ids: set, gh=http_json, raw=http_text, log=lambda m: print(m, file=sys.stderr)) -> list:
    out, seen = [], set()
    for repo in search_repos(gh):
        try:
            entry = inspect(repo, official_ids, gh, raw)
        except Skip as e:
            log(f"跳过 {repo.get('full_name')}：{e}")
            continue
        except Exception as e:  # noqa: BLE001  —— 单个仓库出错不影响其他仓库
            log(f"跳过 {repo.get('full_name')}：读取失败 {e}")
            continue
        if entry["id"] in seen:   # 两个社区仓库撞 id：保留先出现的（按更新时间排序），后者跳过
            log(f"跳过 {repo['full_name']}：包 id {entry['id']} 已被其他社区仓库使用")
            continue
        seen.add(entry["id"])
        out.append(entry)
    return sorted(out, key=lambda e: (-e["stars"], e["id"]))
