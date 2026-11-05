"""Build catalog_cn.csv, download_failures_cn.csv, checksums_en.sha256, domains/*/README_cn.md,
the progress block of README_cn.md and scripts/state/stats_en.json from seeds + state.

  python3 -I scripts/build_catalog_en.py
"""
import collections
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import CACHE, CATS, ROOT, SEEDS, STATE, cat_dir, load, save, window_status  # noqa: E402
from papers_en import entry_meta, seeds  # noqa: E402

OTHER = [Path("/root/time_series_literature"), Path("/root/machine_learning_deep_learning_literature"),
         Path("/root/large_model_multimodal_literature")]

COLS = ["文献编号", "资料类型", "主分类", "交叉分类", "交叉分类依据", "子方向", "研究层级", "文献类型", "时间窗口",
        "首次公开日期", "日期精度", "首次公开依据", "正式发表日期", "标题", "作者", "渠道", "出版者", "卷期页",
        "DOI", "arXiv ID", "PMCID", "原始页面", "全文URL", "本地相对路径", "版本", "版本说明", "来源性质",
        "跨库重复", "下载状态", "核验状态", "SHA256", "行业", "具体生产过程", "任务", "连续/批次", "方法类别",
        "机理信息使用", "数据来源", "数据集", "数据是否公开", "代码链接", "工况数量", "故障类型", "标签条件",
        "在线/离线", "时间切分与验证方式", "是否用故障测试数据调参或设阈值", "评测指标", "点调整评分",
        "字段依据", "全文关键词自动检出（未人工核读）", "选入理由", "三年前/经典保留理由", "内容简介", "阅读优先级",
        "本类前10排名", "前10理由"]


def other_index():
    shas, ids = {}, {}
    for lib in OTHER:
        p = lib / "checksums_en.sha256"
        if p.exists():
            for line in p.read_text(errors="ignore").splitlines():
                if len(line) > 66:
                    shas[line[:64]] = f"{lib.name}/{line[66:].strip()}"
        for c in [lib / "catalog_cn.csv"]:
            if c.exists():
                txt = c.read_text(errors="ignore")
                for m in re.finditer(r"\b(\d{4}\.\d{4,5})\b|\b(10\.\d{4,9}/[^\s,\"]+)", txt):
                    ids.setdefault((m.group(1) or m.group(2)).lower(), lib.name)
    return shas, ids


def fmt_ft(f):
    if not f:
        return ""
    parts = []
    if f["benchmarks"]:
        parts.append("基准/数据：" + "、".join(f"{k}×{v['n']}" for k, v in f["benchmarks"].items()))
    if f["metrics"]:
        parts.append("指标词：" + "、".join(f["metrics"]))
    parts.append("点调整：" + (f"出现（“{f['point_adjust'][:80]}”）" if f["point_adjust"] else "未出现"))
    if f["random_split"]:
        parts.append(f"随机划分相关表述：“{f['random_split'][:80]}”")
    if f["code_links"]:
        parts.append("代码/数据链接：" + " ".join(f["code_links"][:3]))
    return "；".join(parts)


def main():
    cands, meta = load(CACHE / "candidates_en.json", {}), load(CACHE / "metadata_en.json", {})
    reg, mats = load(STATE / "registry_en.json", {}), load(STATE / "materials_en.json", {})
    ft = load(STATE / "fulltext_fields_en.json", {})
    oshas, oids = other_index()
    rows, fails, checks = [], [], []
    stats = {}
    cross_refs = collections.defaultdict(list)
    for cat in [c for c in CATS if int(c) <= 12]:
        st = collections.Counter()
        for s in seeds(cat):
            if s.get("exclude") or s.get("cross_only"):
                continue
            r = reg.get(s["sid"])
            m = entry_meta(s, cands, meta)
            if not r or r["status"] not in ("verified",):
                if r and r["status"] in ("failed", "fail", "pending", "rejected"):
                    fails.append([s["sid"], CATS[cat][1], {"failed": "下载失败", "fail": "已下载但核验未通过（不计数）", "pending": "待人工核验（不计数）",
                                  "rejected": "人工否决（不计数）"}[r["status"]], m["title"],
                                  m["doi"] and f"https://doi.org/{m['doi']}" or (m["arxiv"] and f"https://arxiv.org/abs/{m['arxiv']}"),
                                  (r.get("note", "") if r["status"] != "failed" else "") + " | ".join(r.get("attempts", []))[:600], "已尝试 arXiv/PMC/HAL/出版社开放页面；未绕过访问控制",
                                  "保留缺口或以备选替代"])
                st[r["status"] if r else "untried"] += 1
                continue
            st["verified"] += 1
            a = s.get("ann", {})
            win = window_status(m["first_public_date"])
            win_lbl = "近三年" if win == "近三年" else ("三年前（经典补充，不计入近三年）" if win == "三年前" else win)
            cross = s.get("cross", [])
            for c in cross:
                cross_refs[c].append((s["sid"], m["title"], cat))
            other = oshas.get(r["sha256"]) or oids.get((m["arxiv"] or "").lower()) or oids.get((m["doi"] or "").lower())
            if r.get("reuse") == "已有复用":
                other = str(r.get("version", "")).replace("本机已有文献库复用：", "")
            ver = r.get("version", "")
            vnote = ""
            if m.get("arxiv") and m.get("arxiv_latest") and m["arxiv_latest"] > 1:
                vnote = f"arXiv 最新 v{m['arxiv_latest']}（{m['arxiv_latest_date']}）；v1 {m['first_public_date'] if m['first_public_basis'].startswith('arXiv') else ''}"
            if m.get("arxiv_journal_ref"):
                vnote += f"；作者注 journal_ref：{m['arxiv_journal_ref']}"
            rows.append({
                "文献编号": s["sid"], "资料类型": "论文", "主分类": f"{cat} {CATS[cat][1]}",
                "交叉分类": "；".join(f"{c} {CATS[c][1]}" for c in cross), "交叉分类依据": s.get("cross_reason", ""),
                "子方向": s.get("subtopic", ""), "研究层级": s.get("level", ""), "文献类型": s.get("type", ""),
                "时间窗口": win_lbl, "首次公开日期": m["first_public_date"], "日期精度": m["date_precision"],
                "首次公开依据": m["first_public_basis"], "正式发表日期": m.get("published_date", ""),
                "标题": m["title"], "作者": "; ".join(m["authors"][:12]) + (" 等" if len(m["authors"]) > 12 else ""),
                "渠道": m["venue"], "出版者": m.get("publisher", ""), "卷期页": m.get("vpi", ""),
                "DOI": m["doi"], "arXiv ID": m["arxiv"], "PMCID": m["pmcid"],
                "原始页面": (f"https://doi.org/{m['doi']}" if m["doi"] else f"https://arxiv.org/abs/{m['arxiv']}" if m["arxiv"] else ""),
                "全文URL": r.get("pdf_url", ""), "本地相对路径": r.get("file", ""), "版本": ver, "版本说明": vnote.strip("；"),
                "来源性质": r.get("reuse", "新下载"), "跨库重复": f"是（{other}）" if other else "否",
                "下载状态": "已下载", "核验状态": r.get("note", ""), "SHA256": r.get("sha256", ""),
                "行业": a.get("industry", ""), "具体生产过程": a.get("process", ""), "任务": a.get("task", ""),
                "连续/批次": a.get("process_type", ""), "方法类别": a.get("method", ""), "机理信息使用": a.get("mechanism", ""),
                "数据来源": a.get("data_source", ""), "数据集": a.get("datasets", ""), "数据是否公开": a.get("data_public", ""),
                "代码链接": a.get("code", ""), "工况数量": a.get("modes", ""), "故障类型": a.get("fault_types", ""),
                "标签条件": a.get("labels", ""), "在线/离线": a.get("online", ""), "时间切分与验证方式": a.get("split", ""),
                "是否用故障测试数据调参或设阈值": a.get("fault_data_for_tuning", "待全文核实"), "评测指标": a.get("metrics", ""),
                "点调整评分": a.get("point_adjust", ""), "字段依据": a.get("basis", "摘要") + "（领域字段）",
                "全文关键词自动检出（未人工核读）": fmt_ft(ft.get(s["sid"])), "选入理由": s.get("reason", ""),
                "三年前/经典保留理由": s.get("old_reason", ""), "内容简介": a.get("summary", ""),
                "阅读优先级": s.get("priority", ""), "本类前10排名": s.get("top10_rank", ""), "前10理由": s.get("top10_reason", ""),
            })
            checks.append((r["sha256"], r["file"]))
        stats[cat] = dict(st)
    for cat in ("13", "14"):
        st = collections.Counter()
        for it in load(SEEDS / f"{cat}_{CATS[cat][0]}_seed_cn.json", []):
            if it.get("exclude"):
                continue
            r = mats.get(it["mid"])
            if not r or r["status"] != "verified":
                if r:
                    fails.append([it["mid"], CATS[cat][1], "下载失败", it["title"], it.get("source_page", ""), r.get("note", ""),
                                  "仅使用官方/作者公开渠道，未绕过访问控制", "保留缺口"])
                st["failed" if r else "untried"] += 1
                continue
            st["verified"] += 1
            yr = it.get("edition_year") or it.get("year")
            recent = bool(yr) and int(yr) >= 2023
            files = r["files"]
            path = files[0]["path"] if len(files) == 1 else str(Path(files[0]["path"]).parent)
            for f in files:
                checks.append((f["sha256"], f["path"]))
            other = oshas.get(files[0]["sha256"]) if len(files) == 1 else None
            kind = {"zip": "课程资料包（官方压缩包）", "pdfs": "资料包（多 PDF）", "html_zip": "官方 HTML 离线包（zip）",
                    "pdf": "PDF", "reuse": "PDF（跨库复用）"}[it["kind"]]
            rows.append({
                "文献编号": it["mid"], "资料类型": ("课程资料包" if cat == "13" else "书籍") + f"｜{kind}",
                "主分类": f"{cat} {CATS[cat][1]}", "子方向": it.get("subtopic", ""), "文献类型": "课程讲义" if cat == "13" else "教科书/专著/参考书",
                "时间窗口": "近三年版本" if recent else ("年份待核实" if not yr else "经典/较早版本（教材类年份例外）"),
                "首次公开日期": str(it.get("orig_year") or it.get("year") or ""), "日期精度": "年",
                "首次公开依据": "初版年份" if cat == "14" else "课程学期", "正式发表日期": str(yr or ""),
                "标题": it["title"], "作者": it.get("authors") or it.get("instructors", ""),
                "渠道": it.get("institution") or it.get("publisher", ""), "出版者": it.get("publisher", it.get("institution", "")),
                "DOI": it.get("doi", ""), "原始页面": it.get("source_page", ""),
                "全文URL": it.get("url") or it.get("index_url") or (it.get("urls") or [""])[0],
                "本地相对路径": path, "版本": it.get("edition") or it.get("term", ""),
                "版本说明": it.get("package_scope", ""), "来源性质": r.get("reuse", "新下载"),
                "跨库重复": "是（" + it.get("src", "") + "）" if it["kind"] == "reuse" else ("是（" + other + "）" if other else "否"),
                "下载状态": "已下载", "核验状态": "通过：" + r.get("note", ""),
                "SHA256": files[0]["sha256"] if len(files) == 1 else f"{len(files)} 个文件，见 checksums_en.sha256",
                "字段依据": "官方页面/扉页", "选入理由": it.get("reason", ""), "三年前/经典保留理由": it.get("old_reason", ""),
                "阅读优先级": it.get("priority", ""), "本类前10排名": it.get("top10_rank", ""), "前10理由": it.get("top10_reason", ""),
                "内容简介": it.get("license_note", ""),
            })
        stats[cat] = dict(st)
    with open(ROOT / "catalog_cn.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLS})
    with open(ROOT / "download_failures_cn.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["编号", "分类", "状态", "标题", "原始页面", "尝试记录/原因", "说明", "处理"])
        w.writerows(fails)
    seen = set()
    with open(ROOT / "checksums_en.sha256", "w") as f:
        for sha, p in sorted(checks, key=lambda x: x[1]):
            if p not in seen:
                seen.add(p)
                f.write(f"{sha}  {p}\n")
    save(STATE / "stats_en.json", {"by_cat": stats, "rows": len(rows), "failures": len(fails)})
    # per-category pages
    by = collections.defaultdict(list)
    for r in rows:
        by[r["主分类"][:2]].append(r)
    for cat in CATS:
        d = ROOT / "domains" / cat_dir(cat)
        d.mkdir(parents=True, exist_ok=True)
        lines = [f"# {cat} {CATS[cat][1]}", "", "本页由 `scripts/build_catalog_en.py` 生成。文件只在 papers/、books/、"
                 "university_materials/ 各存一份，这里按编号引用。", ""]
        items = sorted(by.get(cat, []), key=lambda r: (str(r["本类前10排名"]) == "", int(r["本类前10排名"] or 99), r["文献编号"]))
        lines += ["| 编号 | 首次公开 | 子方向 | 标题 | 本地文件 | 优先级 |", "|---|---|---|---|---|---|"]
        for r in items:
            title = r["标题"].replace("|", "/")
            lines.append(f"| {r['文献编号']} | {r['首次公开日期']} | {r['子方向']} | {title} | "
                         f"[{Path(r['本地相对路径']).name}](../../{r['本地相对路径']}) | {r['阅读优先级']}"
                         f"{'（前10 #' + str(r['本类前10排名']) + '）' if r['本类前10排名'] else ''} |")
        if cross_refs.get(cat):
            lines += ["", "## 交叉引用（主分类在其他类，不重复计数）", ""]
            for sid, t, c in cross_refs[cat]:
                if any(r["文献编号"] == sid for r in rows):
                    lines.append(f"- {sid}（主分类 {c} {CATS[c][1]}）：{t}")
        (d / "README_cn.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(stats, ensure_ascii=False), len(rows), "rows;", len(fails), "failures")


if __name__ == "__main__":
    main()
