"""离线自检：python scripts/test_discover.py —— 用假的 GitHub 响应跑 discover，不联网。"""
import json
import urllib.error

from discover import API, discover


def fake(repos: dict):
    """repos: full_name -> {tag, files: {path: obj_or_text}}"""
    def gh(url):
        if "/search/repositories" in url:
            return {"items": [{"full_name": n, "owner": {"login": n.split("/")[0]}, "stargazers_count": r.get("stars", 0)}
                              for n, r in repos.items()]}
        for n, r in repos.items():
            if url == f"{API}/repos/{n}/releases/latest":
                if not r.get("tag"):
                    raise urllib.error.HTTPError(url, 404, "no release", {}, None)
                return {"tag_name": r["tag"], "published_at": "2026-10-01T00:00:00Z"}
            for sub in ("mappings", "recipes"):
                if url.startswith(f"{API}/repos/{n}/contents/{sub}?"):
                    names = [p.split("/", 1)[1] for p in r["files"] if p.startswith(sub + "/")]
                    if not names:
                        raise urllib.error.HTTPError(url, 404, "none", {}, None)
                    return [{"name": x} for x in names]
        raise AssertionError(f"意外的请求 {url}")

    def raw(url):
        for n, r in repos.items():
            prefix = f"https://raw.githubusercontent.com/{n}/{r.get('tag')}/"
            if url.startswith(prefix):
                v = r["files"][url[len(prefix):]]
                return v if isinstance(v, str) else json.dumps(v)
        raise AssertionError(f"意外的下载 {url}")
    return gh, raw


def pack(pid, version="1.0.0", card_api=1):
    card = {"apiVersion": card_api, "id": f"{pid}/list", "version": "1.0.0", "platform": pid, "entity": "item",
            "match": {"path": "/api/list"}, "item_path": "data", "fields": {"id": "id"}, "fixture": "list.fixture.json"}
    return {"platform.json": {"apiVersion": 1, "id": pid, "version": version, "label": pid, "hosts": [f"*.{pid}.com"]},
            "mappings/list.json": card, "mappings/list.fixture.json": {"response": [], "expected": [{}]},
            "recipes/insight.md": "# 洞察配方\n正文"}


gh, raw = fake({
    "alice/good":     {"tag": "v1.0.0", "stars": 5, "files": pack("acme")},
    "bob/badversion": {"tag": "v2.0.0", "files": pack("bobsite", version="1.9.0")},
    "eve/fake":       {"tag": "v1.0.0", "files": pack("amazon")},
    "dan/norelease":  {"tag": None, "files": pack("dansite")},
    "carl/badcard":   {"tag": "1.0.0", "files": pack("carlsite", card_api=2)},
})
skipped = []
got = discover({"amazon"}, gh, raw, log=skipped.append)
assert [e["id"] for e in got] == ["acme"], got
e = got[0]
assert e["base"] == "https://cdn.jsdelivr.net/gh/alice/good@v1.0.0" and e["official"] is False and e["repo"] == "alice/good"
assert e["cards"][0]["path"] == "mappings/list.json" and e["recipes"][0]["title"] == "洞察配方"
reasons = "\n".join(skipped)
for frag in ("不一致", "官方包重名", "没有正式 Release", "apiVersion 必须是 1"):
    assert frag in reasons, (frag, reasons)
print("test_discover ok:", len(got), "收录，", len(skipped), "跳过")
