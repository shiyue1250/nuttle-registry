"""生成 / 校验 index.json：每个平台包的 id、版本、标签、域名、卡列表。

    python scripts/build_index.py                  # 重新生成 index.json
    python scripts/build_index.py --check          # index.json 与目录不一致则退出 1（CI 用）
    python scripts/build_index.py --check-fixtures # 每份样本都是合法 JSON 且带 response / expected
    python scripts/build_index.py --discover       # 同时发现社区包（GitHub 标签 nuttle-pack），写入 community

index.json 四部分：packs 是本仓库目录里的官方包，由目录生成；platforms 是 catalog.json（用户心里的平台 → 模块 → 平台包 / 插件），
原样并入、引用的平台包必须存在；industries 是 industries/*.json 行业包全文（小，直接并入，应用「更新平台列表」时一起拿到）；--check 比对这三部分。community 是社区包，只由 --discover 更新，平时重新生成时原样保留。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORMS = ROOT / "platforms"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def build():
    packs = []
    for pdir in sorted(PLATFORMS.iterdir()):
        pj = pdir / "platform.json"
        if not pj.exists():
            continue
        plat = load(pj)
        cards = []
        for cj in sorted((pdir / "mappings").glob("*.json")):
            if cj.name.endswith(".fixture.json"):
                continue
            card = load(cj)
            cards.append({
                "id": card["id"], "version": card["version"], "entity": card["entity"],
                "verified": card.get("verified"), "fixture": bool(card.get("fixture")),
                "path": cj.relative_to(ROOT).as_posix(),
            })
        recipes = []
        for r in sorted((pdir / "recipes").glob("*.md")):
            if "." in r.stem:          # <名>.en.md 是英文版，挂到同名配方的 locales 下，不是独立配方
                continue
            entry = {"id": f"{plat['id']}/{r.stem}", "title": md_title(r), "path": r.relative_to(ROOT).as_posix()}
            en = r.with_name(f"{r.stem}.en.md")
            if en.exists():
                entry["locales"] = {"en": {"title": md_title(en), "path": en.relative_to(ROOT).as_posix()}}
            recipes.append(entry)
        packs.append({
            "id": plat["id"], "version": plat["version"], "label": plat.get("label", plat["id"]),
            "locales": plat.get("locales"), "hosts": plat.get("hosts", []), "cards": cards, "recipes": recipes,
            "path": pj.relative_to(ROOT).as_posix(), "official": True,
        })
    platforms = load(ROOT / "catalog.json")
    ids = {p["id"] for p in packs}
    for plat in platforms:
        for part in plat["parts"]:
            missing = [x for x in part.get("packs", []) if x not in ids]
            if missing:
                sys.exit(f"catalog.json: {plat['id']}/{part['id']} 引用了不存在的平台包 {missing}")
    industries = [load(f) for f in sorted((ROOT / "industries").glob("*.json"))]
    return {"schema": "schema/mapping-card.schema.json", "packs": packs, "platforms": platforms, "industries": industries}


def md_title(p):
    return p.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()


def check_fixtures():
    bad = []
    for fx in PLATFORMS.glob("*/mappings/*.fixture.json"):
        try:
            d = load(fx)
            if "response" not in d or not isinstance(d.get("expected"), list) or not d["expected"]:
                bad.append(f"{fx}: 缺少 response 或 expected 为空")
        except Exception as e:  # noqa: BLE001
            bad.append(f"{fx}: {e}")
    for line in bad:
        print(line)
    return not bad


def main():
    if "--check-fixtures" in sys.argv:
        sys.exit(0 if check_fixtures() else 1)
    index = build()
    out = ROOT / "index.json"
    old = load(out) if out.exists() else {}
    if "--check" in sys.argv:
        if any(old.get(k) != index[k] for k in ("packs", "platforms", "industries", "schema")):
            print("index.json 过期，运行 python scripts/build_index.py 重新生成")
            sys.exit(1)
        print("index.json 一致")
        return
    if "--discover" in sys.argv:
        from discover import discover
        index["community"] = discover({p["id"] for p in index["packs"]})
    else:
        index["community"] = old.get("community", [])
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"index.json: {len(index['packs'])} 个官方包，{sum(len(p['cards']) for p in index['packs'])} 张卡；"
          f"{len(index['community'])} 个社区包")


if __name__ == "__main__":
    main()
