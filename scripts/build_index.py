"""生成 / 校验 index.json：每个平台包的 id、版本、标签、域名、卡列表。

    python scripts/build_index.py                  # 重新生成 index.json
    python scripts/build_index.py --check          # index.json 与目录不一致则退出 1（CI 用）
    python scripts/build_index.py --check-fixtures # 每份样本都是合法 JSON 且带 response / expected
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
        recipes = [{"id": f"{plat['id']}/{r.stem}", "title": r.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip(),
                    "path": r.relative_to(ROOT).as_posix()} for r in sorted((pdir / "recipes").glob("*.md"))]
        packs.append({
            "id": plat["id"], "version": plat["version"], "label": plat.get("label", plat["id"]),
            "hosts": plat.get("hosts", []), "cards": cards, "recipes": recipes,
            "path": pj.relative_to(ROOT).as_posix(),
        })
    return {"schema": "schema/mapping-card.schema.json", "packs": packs}


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
    text = json.dumps(index, ensure_ascii=False, indent=2) + "\n"
    out = ROOT / "index.json"
    if "--check" in sys.argv:
        if not out.exists() or out.read_text(encoding="utf-8") != text:
            print("index.json 过期，运行 python scripts/build_index.py 重新生成")
            sys.exit(1)
        print("index.json 一致")
        return
    out.write_text(text, encoding="utf-8")
    print(f"index.json: {len(index['packs'])} 个平台包，{sum(len(p['cards']) for p in index['packs'])} 张卡")


if __name__ == "__main__":
    main()
