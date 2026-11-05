"""Screening view: candidates hit by category NN that have a usable full-text route.

  python3 -I scripts/screen_en.py NN [--grep REGEX] [--blocked] [--old] [--limit N] [--claimed]

Columns: short key, first date, route, flags (P process / E equipment / C cyber / X business-process /
TE Tennessee Eastman), venue, title. Candidates already in any seed file are hidden unless --claimed.
Routes known blocked for this host (MDPI, Elsevier, Wiley, T&F, SAGE, AIP, EDP) are hidden unless
--blocked (they may still have an arXiv / PMC copy, which shows up as the route).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import CACHE, CATS, SEEDS, WINDOW_START, load  # noqa: E402
from discover_en import flags  # noqa: E402

BLOCKED = ("10.3390/", "10.1016/", "10.1002/", "10.1155/", "10.1080/", "10.1177/", "10.1063/", "10.1051/",
           "10.1049/", "10.1111/", "10.1021/", "10.1061/", "10.1115/", "10.1142/", "10.3233/")


def route(c):
    if c.get("arxiv"):
        return "arxiv"
    if c.get("pmcid"):
        return "pmc"
    if c.get("hal_pdf"):
        return "hal"
    if c.get("pdf_url"):
        return "pubpdf"
    doi = c.get("doi", "")
    if doi.startswith("10.1109/"):
        return "ieee"
    if doi.startswith(BLOCKED):
        return "BLOCK"
    if doi:
        return "oa:" + doi.split("/")[0][3:]
    return "none"


def claimed():
    keys = set()
    for p in SEEDS.glob("*_seed_cn.json"):
        for s in load(p, []):
            if s.get("key"):
                keys.add(s["key"])
    return keys


def main():
    a = sys.argv[1:]
    cat = a[0]
    grep = a[a.index("--grep") + 1] if "--grep" in a else None
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 500
    cands = load(CACHE / "candidates_en.json", {})
    cl = claimed()
    rows = []
    for k, c in cands.items():
        if cat != "all" and cat not in c.get("hits", {}):
            continue
        if k in cl and "--claimed" not in a:
            continue
        r = route(c)
        if r in ("BLOCK", "none") and "--blocked" not in a:
            continue
        d = c.get("arxiv_date") or c.get("date", "")
        if d and d[:10] < WINDOW_START[:7] and "--old" not in a and len(d) >= 7:
            continue
        t = c["title"] + " " + c.get("abstract", "")
        if grep and not re.search(grep, t, re.I):
            continue
        rows.append((k, d, r, flags(c), c.get("venue", ""), c["title"]))
    rows.sort(key=lambda x: x[5].lower())
    for k, d, r, f, v, t in rows[:limit]:
        print(f"{k[4:44]:40s} {d[:7]:7s} {r[:8]:8s} {f:5s} {v[:18]:18s}| {t[:140]}")
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
