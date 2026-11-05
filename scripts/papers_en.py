"""Paper pipeline for the IPM library (categories 01-12).

  python3 -I scripts/papers_en.py resolve NN            metadata: Crossref (DOI) + arXiv API (arXiv ID)
  python3 -I scripts/papers_en.py download NN [--target 50] [--retry-failed]
                                                        download + verify until NN has --target verified items
  python3 -I scripts/papers_en.py status [NN]           progress lines (fixed sentence format)
  python3 -I scripts/papers_en.py text SID [--pages 2]  first-page text of a downloaded file (manual check)
  python3 -I scripts/papers_en.py manual SID --note '...'   promote a 'pending' item after a manual check
  python3 -I scripts/papers_en.py reject SID --note '...'   mark a downloaded item as rejected (wrong paper etc.)

Seeds: scripts/seeds/NN_<slug>_seed_cn.json (list). Each entry: sid, key (candidate key from
cache/candidates_en.json, e.g. "doi:10.1109/access.2024.1" or "arxiv:2401.01234"), type, subtopic,
priority, reason, optional old_reason, cross, cross_reason, reserve, exclude/exclude_reason,
industry, level (过程层/设备层), pdf_url / landing_url overrides, title/authors for manual entries.

State: scripts/state/registry_en.json keyed by sid. A paper's primary category is the first
category whose seed claims it; a later claim is recorded as duplicate_elsewhere and not counted.
Verification (all hard checks must pass to count): HTTP 200, %PDF- header, pypdf parses,
>= 4 pages, >= 12000 extracted characters (>= 8000 for Chinese), title words (or CJK characters)
>= 0.8 matched in the first two pages, first-author surname found in the first two pages,
references heading found, first page is not supplementary material. Failing only the
author/title soft checks -> 'pending' (manual check needed). Files are staged in a fresh empty
directory outside the library and moved into papers/ only after passing.
"""
import gzip
import hashlib
import html
import json
import re
import shutil
import sys
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import (CACHE, CATS, ROOT, SEEDS, STAGING, STATE, WORK, PYLIB, cat_dir, get_json,  # noqa: E402
                       has_cjk, http, load, norm, save, short_title, surname, title_in_text,
                       title_similarity, window_status, strip_tags)

sys.path.insert(0, str(PYLIB))
import logging  # noqa: E402
logging.getLogger("pypdf").setLevel(logging.ERROR)
from pypdf import PdfReader  # noqa: E402

CAND = CACHE / "candidates_en.json"
META = CACHE / "metadata_en.json"
REG = STATE / "registry_en.json"
TEXT = WORK / "text"
PAPERS = ROOT / "papers"
ATOM = "{http://www.w3.org/2005/Atom}"
ARX = "{http://arxiv.org/schemas/atom}"

OTHER_LIBS = [Path("/root/time_series_literature"), Path("/root/machine_learning_deep_learning_literature"),
              Path("/root/large_model_multimodal_literature")]


def seed_path(cat):
    return SEEDS / f"{cat}_{CATS[cat][0]}_seed_cn.json"


def seeds(cat):
    return load(seed_path(cat), [])


def all_seeds():
    out = []
    for c in CATS:
        if int(c) <= 12:
            out += [(c, s) for s in seeds(c)]
    return out


# ---------------------------------------------------------------- metadata
def crossref_meta(doi):
    d = get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    if not d:
        return None
    m = d["message"]

    def dp(k):
        x = (m.get(k) or {}).get("date-parts") or [[]]
        x = x[0] if x else []
        return "-".join(f"{v:02d}" if i else str(v) for i, v in enumerate(x)) if x and x[0] else ""
    return {
        "title": " ".join(strip_tags((m.get("title") or [""])[0]).split()),
        "authors": [" ".join(x for x in (a.get("given"), a.get("family")) if x) or a.get("name", "")
                    for a in m.get("author", [])],
        "venue": (m.get("container-title") or [""])[0], "publisher": m.get("publisher", ""),
        "published_online": dp("published-online"), "published_print": dp("published-print"),
        "issued": dp("issued"), "posted": dp("posted"), "created": dp("created"),
        "type": m.get("type", ""), "license": [l.get("URL", "") for l in m.get("license", [])],
        "links": [l.get("URL", "") for l in m.get("link", [])],
        "volume": m.get("volume", ""), "issue": m.get("issue", ""), "page": m.get("page", ""),
        "has_preprint": [r.get("id") for r in (m.get("relation", {}) or {}).get("has-preprint", [])],
        "abstract": " ".join(strip_tags(m.get("abstract", "")).split()),
        "language": m.get("language", ""),
    }


def arxiv_meta(ids):
    out = {}
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(
            {"id_list": ",".join(chunk), "max_results": len(chunk)})
        st, body, _, _ = http(url, accept="application/atom+xml")
        if st != 200:
            continue
        for e in ET.fromstring(body).findall(ATOM + "entry"):
            aid = e.findtext(ATOM + "id").rsplit("/abs/", 1)[-1]
            m = re.match(r"(.+?)v(\d+)$", aid)
            base, ver = (m.group(1), int(m.group(2))) if m else (aid, 1)
            out[base] = {
                "title": " ".join(e.findtext(ATOM + "title").split()),
                "authors": [a.findtext(ATOM + "name") for a in e.findall(ATOM + "author")],
                "v1_date": e.findtext(ATOM + "published")[:10],
                "latest_version": ver, "latest_date": e.findtext(ATOM + "updated")[:10],
                "journal_ref": (e.findtext(ARX + "journal_ref") or "").strip(),
                "doi": (e.findtext(ARX + "doi") or "").lower(),
                "comment": " ".join((e.findtext(ARX + "comment") or "").split()),
                "abstract": " ".join((e.findtext(ATOM + "summary") or "").split()),
            }
    return out


def entry_meta(seed, cands, meta):
    """Merged metadata for a seed entry (seed overrides > Crossref/arXiv > candidate cache)."""
    c = cands.get(seed.get("key", ""), {})
    doi = seed.get("doi") or c.get("doi", "")
    arx = seed.get("arxiv") or c.get("arxiv", "")
    cr = meta.get("doi:" + doi, {}) if doi else {}
    ax = meta.get("arxiv:" + arx, {}) if arx else {}
    m = {"doi": doi, "arxiv": arx, "pmcid": seed.get("pmcid") or c.get("pmcid", ""),
         "hal_pdf": seed.get("hal_pdf") or c.get("hal_pdf", ""), "hal": c.get("hal", ""),
         "pdf_url": seed.get("pdf_url") or c.get("pdf_url", "")}
    m["title"] = seed.get("title") or cr.get("title") or ax.get("title") or c.get("title", "")
    m["authors"] = seed.get("authors") or cr.get("authors") or ax.get("authors") or c.get("authors", [])
    m["venue"] = seed.get("venue") or cr.get("venue") or (ax.get("journal_ref") and "arXiv（作者注 journal_ref）") \
        or c.get("venue", "") or ("arXiv 预印本" if arx else "")
    m["publisher"] = cr.get("publisher") or c.get("publisher", "")
    m["abstract"] = c.get("abstract") or cr.get("abstract") or ax.get("abstract", "")
    m["links"] = c.get("links", []) + cr.get("links", [])
    m["license"] = cr.get("license", [])
    # first public date: earliest of arXiv v1 / Crossref online / print / posted / issued (with precision)
    dates = []
    if ax.get("v1_date"):
        dates.append((ax["v1_date"], "arXiv v1 提交日"))
    for k, lab in (("published_online", "Crossref published-online"), ("posted", "Crossref posted"),
                   ("published_print", "Crossref published-print"), ("issued", "Crossref issued")):
        if cr.get(k):
            dates.append((cr[k], lab))
    if c.get("hal_submitted") and not cr and not ax:
        dates.append((c["hal_submitted"], "HAL 提交日"))
    if seed.get("first_public_date"):
        dates.append((seed["first_public_date"], seed.get("first_public_basis", "人工核对")))
    if dates and all(len(d[0]) == 4 for d in dates) and len(cr.get("created", "")) == 10 \
            and cr["created"][:4] == min(d[0] for d in dates):
        dates.append((cr["created"], "Crossref created（DOI 注册日，作为在线日期近似；出版方只给出年份）"))
    if not dates and c.get("date"):
        dates.append((c["date"], c.get("date_basis", "")))
    if dates:
        # prefer the most precise among equally early dates
        dates.sort(key=lambda d: ((d[0] + "-99-99")[:10], -len(d[0])))
        best = dates[0]
        m["first_public_date"], m["first_public_basis"] = best
    else:
        m["first_public_date"], m["first_public_basis"] = "", ""
    m["date_precision"] = {10: "日", 7: "月", 4: "年"}.get(len(m["first_public_date"]), "未知")
    m["published_date"] = cr.get("published_online") or cr.get("issued") or ""
    m["published_print"] = cr.get("published_print", "")
    m["arxiv_latest"] = ax.get("latest_version")
    m["arxiv_latest_date"] = ax.get("latest_date", "")
    m["arxiv_journal_ref"] = ax.get("journal_ref", "")
    m["arxiv_comment"] = ax.get("comment", "")
    m["has_preprint"] = cr.get("has_preprint", [])
    m["vpi"] = c.get("vpi") or " ".join(x for x in (cr.get("volume") and f"Vol. {cr['volume']}", cr.get("issue") and
                                    f"No. {cr['issue']}", cr.get("page") and f"pp./Art. {cr['page']}") if x)
    m["lang"] = "cn" if has_cjk(m["title"]) else "en"
    return m


def resolve(cat):
    cands = load(CAND, {})
    meta = load(META, {})
    todo_doi, todo_arx = [], []
    for s in seeds(cat):
        if s.get("exclude"):
            continue
        c = cands.get(s.get("key", ""), {})
        doi, arx = s.get("doi") or c.get("doi"), s.get("arxiv") or c.get("arxiv")
        if doi and "doi:" + doi not in meta:
            todo_doi.append(doi)
        if arx and "arxiv:" + arx not in meta:
            todo_arx.append(arx)
    for doi in todo_doi:
        r = crossref_meta(doi)
        meta["doi:" + doi] = r or {"error": "crossref lookup failed"}
        save(META, meta)
    if todo_arx:
        res = arxiv_meta(todo_arx)
        for a in todo_arx:
            meta["arxiv:" + a] = res.get(a) or {"error": "arXiv lookup failed"}
        save(META, meta)
    print(f"resolved {len(todo_doi)} DOI + {len(todo_arx)} arXiv for {cat}")


# ---------------------------------------------------------------- PDF location
META_PDF = re.compile(r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)', re.I)
META_PDF2 = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']citation_pdf_url', re.I)


def landing_pdf(url):
    st, body, final, ctype = http(url, accept="text/html,application/pdf")
    if st != 200:
        return None, f"landing HTTP {st}", final
    if body[:5] == b"%PDF-":
        return final, "landing is PDF", final
    txt = body.decode("utf-8", "replace")
    m = META_PDF.search(txt) or META_PDF2.search(txt)
    if m:
        return urllib.parse.urljoin(final, html.unescape(m.group(1))), "citation_pdf_url", final
    return None, "no citation_pdf_url", final


def pdf_candidates(seed, m):
    """Ordered list of (url, version_label, how). Landing pages resolved lazily (url=None, landing)."""
    out = []
    if m.get("pdf_url"):
        out.append((m["pdf_url"], seed.get("version", "出版社官网正式版（开放获取）"), "publisher PDF link"))
    doi = m["doi"]
    if doi.startswith("10.1109/"):
        out.append(("IEEE:" + doi, "出版社正式版（开放获取）", "IEEE stampPDF"))
    if m["pmcid"]:
        out.append(("PMC:" + m["pmcid"], "出版社正式版（PMC 开放获取数据集副本）", "PMC OA dataset (AWS pmc-oa-opendata)"))
    if m.get("hal_pdf"):
        out.append((m["hal_pdf"], "HAL 存档全文（作者存档版本，见 HAL 记录）", "HAL fileMain"))
    if doi and not doi.startswith("10.1109/") and not doi.startswith("10.48550/"):
        for l in m["links"]:
            if l and "doaj" not in l and "api.elsevier" not in l and "mdpi.com" not in l:
                out.append(("LANDING:" + l, "出版社正式版（开放获取）", "landing citation_pdf_url"))
        out.append(("LANDING:https://doi.org/" + doi, "出版社正式版（开放获取）", "DOI landing citation_pdf_url"))
    if m["arxiv"]:
        v = m.get("arxiv_latest")
        out.append((f"https://arxiv.org/pdf/{m['arxiv']}" + (f"v{v}" if v else ""),
                    f"arXiv {m['arxiv']}v{v}（预印本/作者版）" if v else f"arXiv {m['arxiv']}（预印本/作者版）",
                    "arXiv PDF"))
    seen, uniq = set(), []
    for u in out:
        if u[0] not in seen:
            seen.add(u[0])
            uniq.append(u)
    return uniq


def pmc_pdf(pmcid):
    """Latest version in the official PMC Open Access dataset on AWS; returns (url, note)."""
    best = None
    for v in range(1, 6):
        st, body, _, _ = http(f"https://pmc-oa-opendata.s3.amazonaws.com/metadata/{pmcid}.{v}.json",
                              accept="application/json")
        if st != 200:
            break
        try:
            best = json.loads(body)
        except ValueError:
            break
    if not best:
        return None, "PMC OA dataset: no metadata (not in OA subset)"
    if not best.get("pdf_url"):
        return None, f"PMC OA dataset: no PDF (license {best.get('license_code')})"
    path = best["pdf_url"].split("s3://pmc-oa-opendata/", 1)[1].split("?")[0]
    return (f"https://pmc-oa-opendata.s3.amazonaws.com/{path}",
            f"{pmcid} v{best.get('version')}；许可 {best.get('license_code')}；"
            f"{'作者手稿' if best.get('is_manuscript') else '出版社版本'}")


def ieee_pdf(doi):
    st, body, final, _ = http("https://doi.org/" + doi, accept="text/html")
    m = re.search(r"/document/(\d+)", final or "") or re.search(rb'"arnumber":"(\d+)"', body or b"")
    if not m:
        return None, f"IEEE arnumber not found (HTTP {st})"
    num = m.group(1).decode() if isinstance(m.group(1), bytes) else m.group(1)
    return f"https://ieeexplore.ieee.org/stampPDF/getPDF.jsp?tp=&arnumber={num}", "ok"


# ---------------------------------------------------------------- verification
REF_RE = re.compile(r"\n\s*(references|reference|bibliography|literature cited|参\s*考\s*文\s*献)\s*\n|"
                    r"(^|\n)\s*(references|参考文献)\s", re.I)


def extract(path, maxpages=80):
    r = PdfReader(str(path))
    n = len(r.pages)
    texts = []
    for i, p in enumerate(r.pages[:maxpages]):
        try:
            texts.append(p.extract_text() or "")
        except Exception:
            texts.append("")
    return n, texts


def verify(path, m):
    data = path.read_bytes()
    res = {"bytes": len(data)}
    if data[:5] != b"%PDF-":
        return "fail", "无 %PDF- 文件头", res
    try:
        n, texts = extract(path)
    except Exception as e:
        return "fail", f"pypdf 无法解析：{repr(e)[:120]}", res
    full = "\n".join(texts)
    head = "\n".join(texts[:2])
    cjk = has_cjk(m["title"])
    chars = len(full)
    tm = title_in_text(m["title"], head)
    au = m["authors"][0] if m["authors"] else ""
    sn = surname(au)
    if cjk and has_cjk(au):
        au_ok = au[:2] in norm(head) or au[:1] in head
    else:
        au_ok = bool(sn) and sn.lower() in re.sub(r"[^a-z]", "", __import__("common_en").fold(head).lower())
    refs = bool(REF_RE.search(full)) or bool(re.search(r"\[\d+\]\s+[A-Z]", full[-20000:]))
    supp = bool(re.match(r"\s*(supplementary|supporting information)", texts[0] if texts else "", re.I))
    res.update({"pages": n, "chars": chars, "title_match": round(tm, 2), "author": sn, "author_found": au_ok,
                "refs": refs, "supp": supp})
    TEXT.mkdir(parents=True, exist_ok=True)
    hard = []
    if n < 4:
        hard.append(f"仅 {n} 页")
    if chars < (8000 if cjk else 12000):
        hard.append(f"可抽取字符 {chars} 过少")
    if supp:
        hard.append("首页为补充材料")
    if not refs:
        hard.append("未见参考文献节")
    if hard:
        return "fail", "；".join(hard), res, full
    soft = []
    if tm < 0.8:
        soft.append(f"首两页标题匹配 {tm:.2f} < 0.8")
    if not au_ok:
        soft.append(f"首两页未见第一作者 {sn}")
    note = (f"HTTP 200；%PDF 头；pypdf 可解析 {n} 页、{chars} 字符；标题匹配 {tm:.2f}；"
            f"第一作者{'已见' if au_ok else '未见'}；参考文献节已见")
    if soft:
        return "pending", note + "；待人工核对：" + "；".join(soft), res, full
    return "verified", "通过：" + note, res, full


def fname(m, used):
    year = (m["first_public_date"] or "0000")[:4]
    au = m["authors"][0] if m["authors"] else "Anon"
    sn = surname(au) if not has_cjk(au) else None
    if sn is None:
        sn = "".join(ch for ch in au if ch.isalnum())[:4] or "Anon"
    st = short_title(m["title"]) if not has_cjk(m["title"]) else norm(m["title"])[:12]
    base = f"{year}_{sn}_{st}_{m['lang']}"
    name, i = base + ".pdf", 2
    while name in used:
        name, i = f"{base}{i}.pdf", i + 1
    return name


def other_lib_copy(m):
    """Return path of the same paper in an earlier library (arXiv id or DOI in its catalog/registry)."""
    keys = [k for k in (m["arxiv"], m["doi"]) if k]
    if not keys:
        return None
    for lib in OTHER_LIBS:
        for cat in [lib / "catalog_cn.csv"] + list((lib / "scripts").glob("**/*registry*.json")):
            try:
                txt = cat.read_text(errors="ignore")
            except OSError:
                continue
            for k in keys:
                for mm in re.finditer(re.escape(k) + r"(?![0-9])", txt):
                    seg = txt[mm.start():mm.start() + 3000]
                    p = re.search(r"((?:pdfs|papers)/[^\",\s]+?\.pdf)", seg)
                    if p and (lib / p.group(1)).exists():
                        return lib / p.group(1)
    return None


def fetch_one(url):
    stage = Path(tempfile.mkdtemp(prefix="dl_", dir=STAGING))
    st, body, final, ctype = http(url, accept="application/pdf,*/*", timeout=180)
    if st != 200:
        shutil.rmtree(stage, ignore_errors=True)
        return None, f"HTTP {st} {body[:80].decode('utf-8', 'replace') if st is None else ''}".strip(), final
    if body[:5] != b"%PDF-":
        shutil.rmtree(stage, ignore_errors=True)
        return None, f"非 PDF（{ctype[:40]}）", final
    p = stage / "file.pdf"
    p.write_bytes(body)
    return p, "ok", final


def download(cat, target=50, retry_failed=False, only=None):
    STAGING.mkdir(parents=True, exist_ok=True)
    PAPERS.mkdir(exist_ok=True)
    cands, meta, reg = load(CAND, {}), load(META, {}), load(REG, {})
    claimed = {}
    for c, s in all_seeds():
        if s.get("exclude") or s.get("cross_only"):
            continue
        m = entry_meta(s, cands, meta)
        ident = ("doi:" + m["doi"]) if m["doi"] else ("arxiv:" + m["arxiv"]) if m["arxiv"] else "t:" + norm(m["title"])[:80]
        for k in {ident, "t:" + norm(m["title"])[:80]} | ({"arxiv:" + m["arxiv"]} if m["arxiv"] else set()):
            claimed.setdefault(k, s["sid"])
    used = {r.get("file", "").split("/")[-1] for r in reg.values()}
    hashes = {r["sha256"]: sid for sid, r in reg.items() if r.get("sha256") and r["status"] in ("verified", "pending")}

    def n_ok():
        return sum(1 for s in seeds(cat) if reg.get(s["sid"], {}).get("status") == "verified")

    for s in sorted(seeds(cat), key=lambda s: (bool(s.get("reserve")), s["sid"])):
        if n_ok() >= target:
            break
        sid = s["sid"]
        if only and sid not in only:
            continue
        r = reg.get(sid, {})
        if s.get("exclude") or s.get("cross_only") or r.get("status") in ("verified", "pending", "rejected"):
            continue
        if r.get("status") == "failed" and not retry_failed:
            continue
        m = entry_meta(s, cands, meta)
        ident = ("doi:" + m["doi"]) if m["doi"] else ("arxiv:" + m["arxiv"]) if m["arxiv"] else "t:" + norm(m["title"])[:80]
        owner = claimed.get(ident) or claimed.get("t:" + norm(m["title"])[:80])
        if owner and owner != sid:
            reg[sid] = {"status": "duplicate_elsewhere", "note": f"同一文献已由 {owner} 认领"}
            save(REG, reg)
            continue
        attempts, got = [], None
        reused = other_lib_copy(m)
        if reused:
            stage = Path(tempfile.mkdtemp(prefix="reuse_", dir=STAGING))
            p = stage / "file.pdf"
            shutil.copyfile(reused, p)
            got = (p, f"本机已有文献库复用：{reused}", "已有复用", str(reused))
        else:
            for url, ver, how in pdf_candidates(s, m):
                real = url
                if url.startswith("PMC:"):
                    real, why = pmc_pdf(url[4:])
                    if not real:
                        attempts.append(f"{how}: {why}")
                        continue
                    ver = f"{ver}（{why}）"
                if url.startswith("IEEE:"):
                    real, why = ieee_pdf(url[5:])
                    if not real:
                        attempts.append(f"{how}: {why}")
                        continue
                if url.startswith("LANDING:"):
                    real, why, final = landing_pdf(url[8:])
                    if not real:
                        attempts.append(f"{how} {url[8:]}: {why}")
                        continue
                    if "mdpi.com" in real:
                        attempts.append(f"{how}: MDPI 站点对本机 403，跳过")
                        continue
                p, why, final = fetch_one(real)
                if p is None:
                    attempts.append(f"{how} {real}: {why}")
                    continue
                got = (p, ver, how, real)
                break
        if not got:
            reg[sid] = {"status": "failed", "cat": cat, "attempts": attempts, "title": m["title"]}
            save(REG, reg)
            print(f"{sid} FAILED  {m['title'][:70]} :: {' | '.join(attempts)[:200]}")
            continue
        p, ver, how, real = got
        out = verify(p, m)
        status, note, res = out[:3]
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if status in ("verified", "pending") and sha in hashes and hashes[sha] != sid:
            status, note = "duplicate_elsewhere", f"哈希与 {hashes[sha]} 相同"
        rec = {"status": status, "cat": cat, "note": note, "checks": res, "pdf_url": real, "how": how,
               "version": ver, "sha256": sha, "title": m["title"], "attempts": attempts,
               "reuse": "已有复用" if reused else "新下载"}
        if status in ("verified", "pending"):
            name = fname(m, used)
            used.add(name)
            dest = PAPERS / name
            if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() != sha:
                raise SystemExit(f"refusing to overwrite {dest}")
            shutil.move(str(p), dest)
            rec["file"] = f"papers/{name}"
            hashes[sha] = sid
            with gzip.open(TEXT / f"{sid}.txt.gz", "wt", errors="replace") as f:
                f.write(out[3])
        shutil.rmtree(p.parent, ignore_errors=True)
        reg[sid] = rec
        save(REG, reg)
        print(f"{sid} {status.upper():9s} {m['title'][:70]} :: {note[:120]}")
    status_line(cat)


def status_line(cat, verbose=True):
    reg = load(REG, {})
    ss = [s for s in seeds(cat) if not s.get("exclude") and not s.get("cross_only")]
    cands, meta = load(CAND, {}), load(META, {})
    ok = [s for s in ss if reg.get(s["sid"], {}).get("status") == "verified"]
    pend = [s for s in ss if reg.get(s["sid"], {}).get("status") == "pending"]
    fail = [s for s in ss if reg.get(s["sid"], {}).get("status") == "failed"]
    recent = sum(1 for s in ok if window_status(entry_meta(s, cands, meta)["first_public_date"]) == "近三年")
    pct = f"{recent}/{len(ok)}（{100 * recent / len(ok):.1f}%）" if ok else "-"
    print(f"[{cat} {CATS[cat][1]}] 已核验完整资料 {len(ok)} / 目标约 50；待核验 {len(pend)}；下载失败 {len(fail)}。"
          f" 近三年 {pct}")
    if verbose:
        for s in pend:
            print("   pending", s["sid"], reg[s["sid"]]["note"][-90:])


def show_text(sid, pages=2):
    reg = load(REG, {})
    p = ROOT / reg[sid]["file"]
    _, texts = extract(p, pages)
    print("\n---page---\n".join(t[:3000] for t in texts))


def set_status(sid, new, note):
    reg = load(REG, {})
    r = reg[sid]
    if new == "verified":
        assert r["status"] == "pending", "only pending items can be promoted"
        r["note"] = r["note"].split("；待人工核对")[0] + f"；人工核对通过：{note}"
    else:
        r["note"] = r.get("note", "") + f"；人工否决：{note}"
        if r.get("file"):
            rej = WORK / "rejected"
            rej.mkdir(exist_ok=True)
            shutil.move(str(ROOT / r["file"]), rej / Path(r["file"]).name)
            r["file_rejected"] = r.pop("file")
    r["status"] = new
    save(REG, reg)
    print(sid, new)


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d  # noqa: E731
    if a[0] == "resolve":
        resolve(a[1])
    elif a[0] == "download":
        download(a[1], int(opt("--target", 50)), "--retry-failed" in a,
                 set(opt("--only").split(",")) if opt("--only") else None)
    elif a[0] == "status":
        for c in ([a[1]] if len(a) > 1 else [c for c in CATS if int(c) <= 12]):
            status_line(c, verbose=len(a) > 1)
    elif a[0] == "text":
        show_text(a[1], int(opt("--pages", 2)))
    elif a[0] == "manual":
        set_status(a[1], "verified", opt("--note"))
    elif a[0] == "reject":
        set_status(a[1], "rejected", opt("--note"))
