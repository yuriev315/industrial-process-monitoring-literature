"""Course packages (category 13) and books (category 14).

  python3 -I scripts/materials_en.py fetch 13|14 [--only MID] [--retry-failed]
  python3 -I scripts/materials_en.py status 13|14

Manifest: scripts/seeds/13_university_courses_seed_cn.json, scripts/seeds/14_books_references_seed_cn.json
(list of items). Item kinds:
  pdf      one official PDF (whole book / whole lecture-notes volume) -> books/<name>.pdf or
           university_materials/<name>.pdf
  pdfs     several official PDFs that together form the whole work (book chapters, every lecture of a
           course); `urls` lists them, or `index_url` + `link_regex` collects them from the official
           index page. Every file must pass -> <dir>/<name>/NN_<file>_<lang>.pdf
  zip      an official "download course" archive (e.g. MIT OCW); kept as is (<name>.zip); every PDF inside
           must parse and at least `min_pdfs` PDFs must be present
  html_zip an official HTML book/course: `index_url` + `link_regex` give the table of contents; every
           listed page is saved with wget (page requisites, converted links) and the set is zipped
           (<name>.zip) for offline reading. Every page must return 200 with >= `min_chars` text.
Hard checks for PDFs: %PDF- header, pypdf parses, >= min_pages pages (per item / per file),
`title_phrase` found in the first 10 pages of the main file (or of the index page for html_zip).
Results: scripts/state/materials_en.json. Failed items are never counted.
"""
import hashlib
import html as htmlmod
import io
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import CATS, ROOT, SEEDS, STAGING, STATE, PYLIB, UA, http, load, save, norm  # noqa: E402

sys.path.insert(0, str(PYLIB))
import logging  # noqa: E402
logging.getLogger("pypdf").setLevel(logging.ERROR)
from pypdf import PdfReader  # noqa: E402

RES = STATE / "materials_en.json"


def manifest(cat):
    return load(SEEDS / f"{cat}_{CATS[cat][0]}_seed_cn.json", [])


def outdir(cat):
    return ROOT / ("university_materials" if cat == "13" else "books")


def pdf_info(data, phrase=None, head_pages=10):
    if data[:5] != b"%PDF-":
        return None, "无 %PDF- 头"
    try:
        r = PdfReader(io.BytesIO(data))
        n = len(r.pages)
        head = ""
        if phrase:
            for p in r.pages[:head_pages]:
                try:
                    head += (p.extract_text() or "") + "\n"
                except Exception:
                    pass
        found = (norm(phrase) in norm(head)) if phrase else None
        return {"pages": n, "phrase_found": found}, "ok"
    except Exception as e:
        return None, f"pypdf 无法解析：{repr(e)[:100]}"


def get(url, timeout=600):
    st, body, final, ctype = http(url, accept="*/*", timeout=timeout, max_bytes=1_500_000_000)
    return st, body, final, ctype


def links_from(index_url, regex):
    st, body, final, _ = get(index_url)
    if st != 200:
        return None, f"索引页 HTTP {st}"
    txt = body.decode("utf-8", "replace")
    out = []
    for h in re.findall(r'href=["\']([^"\'#]+)', txt):
        u = urllib.parse.urljoin(final, htmlmod.unescape(h))
        if re.search(regex, u) and u not in out:
            out.append(u)
    return out, "ok"


def safe(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")[:60]


def do_pdf(it, dest_dir, stage):
    url = it.get("url")
    if not url and it.get("landing"):
        from papers_en import landing_pdf
        url, why, _ = landing_pdf(it["landing"])
        if not url:
            return None, f"落地页未给出 citation_pdf_url（{why}）"
    st, body, final, ct = get(url)
    if st != 200:
        return None, f"HTTP {st}"
    info, why = pdf_info(body, it.get("title_phrase"))
    if not info:
        return None, why
    if info["pages"] < it.get("min_pages", 50):
        return None, f"仅 {info['pages']} 页 < {it.get('min_pages', 50)}"
    if it.get("title_phrase") and not info["phrase_found"]:
        return None, f"前 10 页未见书名短语“{it['title_phrase']}”"
    name = it["name"] + ".pdf"
    (stage / name).write_bytes(body)
    return {"files": [{"path": name, "url": final, "pages": info["pages"],
                       "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}],
            "note": f"PDF {info['pages']} 页；书名短语已见" if it.get("title_phrase") else f"PDF {info['pages']} 页"}, "ok"


def do_pdfs(it, dest_dir, stage):
    urls = it.get("urls")
    if not urls:
        urls, why = links_from(it["index_url"], it["link_regex"])
        if not urls:
            return None, f"未从索引页取得文件链接（{why}）"
    if len(urls) < it.get("min_files", 1):
        return None, f"索引页仅 {len(urls)} 个文件 < {it.get('min_files')}"
    pkg = stage / it["name"]
    pkg.mkdir()
    files, total = [], 0
    for i, u in enumerate(urls, 1):
        st, body, final, ct = get(u)
        if st != 200:
            return None, f"第 {i} 个文件 HTTP {st}: {u}"
        info, why = pdf_info(body, it.get("title_phrase") if i == 1 else None)
        if not info:
            return None, f"第 {i} 个文件 {u}: {why}"
        if info["pages"] < it.get("min_pages_each", 1):
            return None, f"第 {i} 个文件仅 {info['pages']} 页"
        base = Path(urllib.parse.urlparse(final).path).stem
        fn = f"{i:02d}_{safe(base)}_{it.get('lang', 'en')}.pdf"
        (pkg / fn).write_bytes(body)
        total += info["pages"]
        files.append({"path": f"{it['name']}/{fn}", "url": final, "pages": info["pages"],
                      "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
    if total < it.get("min_pages", 1):
        return None, f"合计仅 {total} 页 < {it.get('min_pages')}"
    return {"files": files, "note": f"{len(files)} 个 PDF 全部下载并可解析，合计 {total} 页"
            + (f"；文件链接取自官方索引页 {it['index_url']}" if it.get("index_url") else "")}, "ok"


def do_zip(it, dest_dir, stage):
    st, body, final, ct = get(it["url"], timeout=1200)
    if st != 200:
        return None, f"HTTP {st}"
    try:
        z = zipfile.ZipFile(io.BytesIO(body))
        bad = z.testzip()
    except Exception as e:
        return None, f"zip 无法打开：{repr(e)[:80]}"
    if bad:
        return None, f"zip 校验失败：{bad}"
    pdfs = [n for n in z.namelist() if n.lower().endswith(".pdf")]
    pages, broken = 0, []
    for n in pdfs:
        info, why = pdf_info(z.read(n))
        if not info:
            broken.append(n)
        else:
            pages += info["pages"]
    if broken:
        return None, f"{len(broken)} 个 PDF 不可解析，如 {broken[0]}"
    if len(pdfs) < it.get("min_pdfs", 1):
        return None, f"仅 {len(pdfs)} 个 PDF < {it.get('min_pdfs')}"
    must = it.get("must_contain", [])
    names = " ".join(z.namelist()).lower()
    miss = [m for m in must if m.lower() not in names]
    if miss:
        return None, f"缺少应有文件：{miss}"
    name = it["name"] + ".zip"
    (stage / name).write_bytes(body)
    return {"files": [{"path": name, "url": final, "pdfs": len(pdfs), "pdf_pages": pages,
                       "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}],
            "note": f"官方课程压缩包，zip 完整性通过，含 {len(z.namelist())} 个文件、{len(pdfs)} 个 PDF（合计 {pages} 页）全部可解析"}, "ok"


def do_html_zip(it, dest_dir, stage):
    pages = [it["index_url"]] + [u for u in (links_from(it["index_url"], it["link_regex"])[0] or [])
                                 if u.split("#")[0] != it["index_url"]]
    pages += [u for u in it.get("extra_pages", []) if u not in pages]
    if len(pages) < it.get("min_files", 2):
        return None, f"目录只解析到 {len(pages)} 页"
    site = stage / "site"
    site.mkdir()
    texts = []
    for u in pages:
        st, body, final, ct = get(u)
        if st != 200 or "html" not in ct:
            return None, f"页面 HTTP {st} {ct}: {u}"
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", " ",
                                                                   body.decode("utf-8", "replace"))))
        if len(txt) < it.get("min_chars", 1500):
            return None, f"页面正文过短（{len(txt)} 字符）: {u}"
        texts.append(txt)
        r = subprocess.run(["wget", "-q", "-E", "-k", "-p", "-np", "-e", "robots=on", "--wait=2",
                            "-U", UA, "-P", str(site), u], capture_output=True, timeout=600)
        if r.returncode not in (0, 8):
            return None, f"wget 失败 {r.returncode}: {u}"
    if it.get("title_phrase") and norm(it["title_phrase"]) not in norm(texts[0]):
        return None, f"首页未见名称短语“{it['title_phrase']}”"
    name = it["name"] + ".zip"
    with zipfile.ZipFile(stage / name, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(site.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(site))
        z.writestr("PAGES_en.txt", "\n".join(pages) + "\n")
    data = (stage / name).read_bytes()
    return {"files": [{"path": name, "url": it["index_url"], "html_pages": len(pages),
                       "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}],
            "note": f"官方 HTML，目录页列出的 {len(pages)} 个页面全部 HTTP 200 且正文≥{it.get('min_chars', 1500)} 字符，"
                    f"wget 保存页面资源并打包（含页面清单 PAGES_en.txt）"}, "ok"


def do_reuse(it, dest_dir, stage):
    """Copy a verified PDF from an earlier local library, then re-run the PDF checks."""
    src = Path(it["src"])
    if not src.exists():
        return None, f"来源文件不存在：{src}"
    body = src.read_bytes()
    info, why = pdf_info(body, it.get("title_phrase"))
    if not info:
        return None, why
    if info["pages"] < it.get("min_pages", 50):
        return None, f"仅 {info['pages']} 页"
    if it.get("title_phrase") and not info["phrase_found"]:
        return None, f"前 10 页未见书名短语“{it['title_phrase']}”"
    name = it["name"] + ".pdf"
    (stage / name).write_bytes(body)
    return {"files": [{"path": name, "url": it.get("url", ""), "copied_from": str(src), "pages": info["pages"],
                       "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}],
            "reuse": "已有复用（跨库重复）",
            "note": f"复制自本机已有文献库 {src}（该库已核验），本库重新核验：PDF {info['pages']} 页、书名短语已见"}, "ok"


KINDS = {"reuse": do_reuse, "pdf": do_pdf, "pdfs": do_pdfs, "zip": do_zip, "html_zip": do_html_zip}


def fetch(cat, only=None, retry_failed=False):
    res = load(RES, {})
    dest = outdir(cat)
    dest.mkdir(exist_ok=True)
    STAGING.mkdir(parents=True, exist_ok=True)
    for it in manifest(cat):
        mid = it["mid"]
        if only and mid != only:
            continue
        r = res.get(mid, {})
        if it.get("exclude") or r.get("status") == "verified":
            continue
        if r.get("status") == "failed" and not retry_failed and not only:
            continue
        stage = Path(tempfile.mkdtemp(prefix="mat_", dir=STAGING))
        try:
            out, why = KINDS[it["kind"]](it, dest, stage)
        except Exception as e:
            out, why = None, f"异常：{repr(e)[:150]}"
        if not out:
            res[mid] = {"status": "failed", "cat": cat, "note": why, "title": it["title"]}
            print(f"{mid} FAILED {it['title'][:60]} :: {why}")
        else:
            for f in out["files"]:
                target = dest / f["path"]
                if target.exists():
                    raise SystemExit(f"refusing to overwrite {target}")
            for p in stage.iterdir():
                if p.name != "site":
                    shutil.move(str(p), dest / p.name)
            for f in out["files"]:
                f["path"] = f"{dest.name}/{f['path']}"
            res[mid] = {"status": "verified", "cat": cat, "title": it["title"], **out}
            print(f"{mid} VERIFIED {it['title'][:60]} :: {out['note'][:100]}")
        shutil.rmtree(stage, ignore_errors=True)
        save(RES, res)
    status(cat)


def status(cat):
    res = load(RES, {})
    items = [i for i in manifest(cat) if not i.get("exclude")]
    ok = [i for i in items if res.get(i["mid"], {}).get("status") == "verified"]
    fail = [i for i in items if res.get(i["mid"], {}).get("status") == "failed"]
    pend = [i for i in items if i["mid"] not in res]
    print(f"[{cat} {CATS[cat][1]}] 已核验完整资料 {len(ok)} / 目标约 50；待核验 {len(pend)}；下载失败 {len(fail)}。")
    for i in fail:
        print("   failed", i["mid"], i["title"][:50], "::", res[i["mid"]]["note"][:120])


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "fetch":
        fetch(a[1], a[a.index("--only") + 1] if "--only" in a else None, "--retry-failed" in a)
    elif a[0] == "status":
        status(a[1])
