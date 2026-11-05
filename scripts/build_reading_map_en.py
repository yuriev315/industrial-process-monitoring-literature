"""Generate reading_map_cn.md: top-10 per category (ranked entries first, then filled by priority
高 > 中 > 低 among verified items, reason = top10_reason or 选入理由) plus the hand-written reading route
in scripts/reading_route_cn.md.

  python3 -I scripts/build_reading_map_en.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import CATS, ROOT, SCRIPTS  # noqa: E402

PRI = {"高": 0, "中": 1, "低": 2, "": 3}


def main():
    rows = list(csv.DictReader(open(ROOT / "catalog_cn.csv", encoding="utf-8-sig")))
    out = ["# 阅读地图", "", "由 `scripts/build_reading_map_en.py` 从 catalog_cn.csv 生成。每类前 10 份：先取筛选时标注的前 10 排名"
           "（仅限已核验条目），不足 10 份时按阅读优先级（高 > 中 > 低）与编号补足，补足项的理由取“选入理由”。"
           "简介与理由依据摘要或官方页面，未通读全文。", ""]
    route = SCRIPTS / "reading_route_cn.md"
    if route.exists():
        out += [route.read_text().rstrip(), ""]
    out += ["## 每类优先阅读的 10 份", ""]
    for cat in CATS:
        items = [r for r in rows if r["主分类"].startswith(cat + " ")]
        ranked = sorted([r for r in items if r["本类前10排名"]], key=lambda r: int(r["本类前10排名"]))
        rest = sorted([r for r in items if not r["本类前10排名"]], key=lambda r: (PRI.get(r["阅读优先级"], 3), r["文献编号"]))
        top = (ranked + rest)[:10]
        out += [f"### {cat} {CATS[cat][1]}", "", "| # | 编号 | 首次公开/版本 | 标题 | 理由 | 文件 |", "|---|---|---|---|---|---|"]
        for i, r in enumerate(top, 1):
            why = r["前10理由"] or ("（补足）" + r["选入理由"])
            ver = r["首次公开日期"] if r["资料类型"] == "论文" else (r["版本"] or r["正式发表日期"])
            out.append(f"| {i} | {r['文献编号']} | {ver} | {r['标题'].replace('|', '/')} | {why.replace('|', '/')} | "
                       f"[{Path(r['本地相对路径']).name}]({r['本地相对路径']}) |")
        out.append("")
    (ROOT / "reading_map_cn.md").write_text("\n".join(out) + "\n")
    print("ok")


if __name__ == "__main__":
    main()
