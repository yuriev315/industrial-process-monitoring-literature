"""Validate a category seed file before download.

  python3 -I scripts/seedcheck_en.py NN

Checks: JSON list, unique sid with NN- prefix, key present in cache/candidates_en.json (or manual
title + pdf_url), required fields, old_reason for items first published before the window,
<= 5 pre-window items among main (non-reserve) entries, blocked-only routes, keys claimed by
another category's seed file, annotation fields present. Prints subtopic / route / level counts.
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import CACHE, CATS, SEEDS, WINDOW_START, load  # noqa: E402
from screen_en import route  # noqa: E402

REQ = ["sid", "type", "subtopic", "priority", "reason", "level", "ann"]
ANN = ["industry", "process", "task", "process_type", "method", "mechanism", "data_source", "datasets",
       "data_public", "code", "modes", "fault_types", "labels", "online", "split", "fault_data_for_tuning",
       "metrics", "point_adjust", "summary", "basis"]


def main(cat):
    path = SEEDS / f"{cat}_{CATS[cat][0]}_seed_cn.json"
    seeds = load(path, None)
    if not isinstance(seeds, list):
        raise SystemExit(f"{path} missing or not a list")
    cands = load(CACHE / "candidates_en.json", {})
    others = {}
    for p in SEEDS.glob("*_seed_cn.json"):
        if p != path:
            for s in load(p, []):
                if s.get("key") and not s.get("cross_only") and not s.get("exclude"):
                    others[s["key"]] = s["sid"]
    errs, warns = [], []
    sids = collections.Counter(s.get("sid") for s in seeds)
    for sid, n in sids.items():
        if n > 1:
            errs.append(f"duplicate sid {sid}")
    keys = collections.Counter(s.get("key") for s in seeds if s.get("key"))
    for k, n in keys.items():
        if n > 1:
            errs.append(f"duplicate key {k}")
    old_main, sub, rt, lvl, typ = 0, collections.Counter(), collections.Counter(), collections.Counter(), collections.Counter()
    main_n = res_n = 0
    for s in seeds:
        if s.get("exclude") or s.get("cross_only"):
            continue
        sid = s.get("sid", "?")
        if not str(sid).startswith(cat + "-"):
            errs.append(f"{sid}: sid must start with {cat}-")
        for f in REQ:
            if f not in s:
                errs.append(f"{sid}: missing {f}")
        for f in ANN:
            if f not in s.get("ann", {}):
                errs.append(f"{sid}: ann missing {f}")
        c = cands.get(s.get("key", ""))
        if c is None and not (s.get("title") and s.get("pdf_url")):
            errs.append(f"{sid}: key {s.get('key')} not in candidates (and no manual title+pdf_url)")
            continue
        c = c or {}
        r = route(c) if c else "manual"
        if r in ("BLOCK", "none") and not s.get("pdf_url"):
            warns.append(f"{sid}: route {r} (no legal full-text route known)")
        if s.get("key") in others:
            warns.append(f"{sid}: key also claimed by {others[s['key']]} (earlier category wins)")
        d = s.get("first_public_date") or c.get("arxiv_date") or c.get("date", "")
        old = bool(d) and (d + "-12-31")[:10] < WINDOW_START if len(d) == 4 else bool(d) and d[:10] < WINDOW_START
        if old and not s.get("old_reason"):
            errs.append(f"{sid}: pre-window ({d}) without old_reason")
        if s.get("reserve"):
            res_n += 1
        else:
            main_n += 1
            old_main += old
        sub[s.get("subtopic")] += 1
        rt[r.split(":")[0]] += 1
        lvl[s.get("level")] += 1
        typ[s.get("type")] += 1
    if old_main > 5:
        errs.append(f"{old_main} pre-window items among main entries (max 5)")
    print(f"{path.name}: main {main_n}, reserve {res_n}, pre-window main {old_main}")
    print("subtopics:", dict(sub))
    print("routes:", dict(rt), "| levels:", dict(lvl), "| types:", dict(typ))
    for w in warns:
        print("WARN", w)
    for e in errs:
        print("ERROR", e)
    print("OK" if not errs else f"{len(errs)} errors")


if __name__ == "__main__":
    main(sys.argv[1])
