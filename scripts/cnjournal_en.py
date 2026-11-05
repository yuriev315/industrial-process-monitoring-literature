"""Chinese-language candidates from 自动化学报 (Acta Automatica Sinica, www.aas.net.cn; free full text).

  python3 -I scripts/cnjournal_en.py scan [--from 2023-11] [--to 2026-10]
      read every issue table of contents in the range, keep articles whose Chinese title matches the
      process-monitoring keyword list, then read each kept article page for citation_* metadata,
      网络出版日期 and abstract; merge into cache/candidates_en.json with hits under category "cn"
      (key doi:10.16383/..., pdf_url = the journal's own PDF link). Logged to state/search_log_en.jsonl.
"""
import html as htmlmod
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import CACHE, STATE, http, load, save, append_jsonl  # noqa: E402

KW = re.compile(r"过程监测|过程监控|故障检测|故障诊断|故障预警|异常检测|软测量|质量预测|质量相关|批次|间歇过程|多工况|多模态过程|"
                r"非平稳|根因|故障溯源|故障传播|工业过程|化工过程|流程工业|工业大数据|数字孪生|状态估计|贝叶斯滤波|"
                r"慢特征|主元|偏最小二乘|潜变量|高炉|冶金|发酵|污水|电厂|过程控制|运行状态|工况")
BASE = "https://www.aas.net.cn"


def months(a, b):
    y, m = map(int, a.split("-"))
    while f"{y}-{m:02d}" <= b:
        yield y, m
        m += 1
        if m > 12:
            y, m = y + 1, 1


def meta_page(doi):
    st, body, _, _ = http(f"{BASE}/cn/article/doi/{doi}", accept="text/html")
    if st != 200:
        return None
    t = body.decode("utf-8", "replace")
    get = lambda k: [htmlmod.unescape(x) for x in re.findall(rf'name="citation_{k}" content="([^"]*)"', t)]  # noqa: E731
    online = re.search(r"网络出版日期:(?:&nbsp;|\s|<[^>]+>)*(\d{4}-\d{2}-\d{2})", t)
    abs_m = re.search(r'name="citation_abstract" content="([^"]*)"', t) or re.search(r'name="description" content="([^"]*)"', t)
    pdf = re.search(r'(//www\.aas\.net\.cn/+cn/article/pdf/preview/[^"\']+\.pdf)', t)
    return {
        "doi": doi.lower(), "title": (get("title") or [""])[0], "authors": get("author"),
        "date": online.group(1) if online else (get("online_date") or get("date") or [""])[0],
        "date_basis": "期刊官网网络出版日期" if online else "期刊官网 citation_online_date",
        "venue": "自动化学报", "publisher": "《自动化学报》编辑部（中国自动化学会、中国科学院自动化研究所）",
        "abstract": htmlmod.unescape(abs_m.group(1)) if abs_m else "",
        "keywords": (get("keywords") or [""])[0],
        "pdf_url": "https:" + re.sub(r"^//www\.aas\.net\.cn/+", "//www.aas.net.cn/", pdf.group(1)) if pdf else "",
        "vpi": f"{(get('year') or [''])[0]}, {(get('volume') or [''])[0]}({(get('issue') or [''])[0]}): {(get('firstpage') or [''])[0]}",
        "lang": "zh",
    }


def scan(a="2023-11", b="2026-10"):
    import fcntl
    kept, seen = [], set()
    for y, m in months(a, b):
        st, body, _, _ = http(f"{BASE}/cn/article/{y}/{m}", accept="text/html")
        if st != 200:
            print("issue", y, m, "HTTP", st)
            continue
        t = body.decode("utf-8", "replace")
        for doi, title in re.findall(r'href="//www\.aas\.net\.cn/cn/article/doi/(10\.16383/[^"#?]+)"[^>]*>\s*([^<]{6,120})<', t):
            title = htmlmod.unescape(title).strip()
            if doi in seen or not KW.search(title):
                continue
            seen.add(doi)
            kept.append((doi, title, f"{y}-{m:02d}"))
    print("kept", len(kept))
    recs = []
    for doi, title, issue in kept:
        r = meta_page(doi)
        if not r or not r["title"]:
            print("meta failed", doi)
            continue
        r["issue"] = issue
        recs.append(r)
        print(issue, doi, r["date"], r["title"][:40])
    new = 0
    with open(STATE / "discover.lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        cands = load(CACHE / "candidates_en.json", {})
        for r in recs:
            key = "doi:" + r["doi"]
            new += key not in cands
            c = cands.setdefault(key, {"aliases": [], "hits": {}})
            c.update({k: v for k, v in r.items() if v})
            c["hits"].setdefault("cn", ["cnAAS"])
        save(CACHE / "candidates_en.json", cands)
    append_jsonl(STATE / "search_log_en.jsonl", {
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "cat": "cn", "qid": "cnAAS",
        "src": "aas", "q": f"《自动化学报》官网 {a}～{b} 各期目录，中文标题关键词：{KW.pattern}", "start": a,
        "total": len(kept), "fetched": len(kept), "new": new})


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "scan":
        scan(a[a.index("--from") + 1] if "--from" in a else "2023-11", a[a.index("--to") + 1] if "--to" in a else "2026-10")
