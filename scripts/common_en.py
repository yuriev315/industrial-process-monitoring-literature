"""Shared helpers for the industrial process monitoring (IPM) literature library.

Paths, per-host rate limiting (cross-process flock), bounded-retry HTTP GET,
text normalisation, the three-year window and atomic JSON load/save.

Rate limits: arXiv >= 5 s between requests (API and PDF share one budget),
Crossref / DOAJ / Europe PMC >= 1.5 s, every other host >= 3 s.
4xx other than 429 is never retried.
"""
import fcntl
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
CACHE = SCRIPTS / "cache"
STATE = SCRIPTS / "state"
SEEDS = SCRIPTS / "seeds"
WORK = Path(os.environ.get("IPM_WORK", "/root/.cache/ipm_lit"))   # on disk, outside the library
STAGING = WORK / "staging"
PYLIB = WORK / "pylib"
LOCK_DIR = WORK / "locks"
UA = "Mozilla/5.0 (compatible; ipm_literature/1.0; personal literature collection, low request rate)"

SEARCH_DATE = "2026-10-29"
WINDOW_START, WINDOW_END = "2023-10-29", "2026-10-29"

CATS = {
    "01": ("fundamentals_reviews", "工业过程监控基础与综述"),
    "02": ("statistical_latent", "统计与潜变量方法"),
    "03": ("ml_dl_monitoring", "机器学习与深度学习监控"),
    "04": ("anomaly_incipient", "异常检测与早期故障检测"),
    "05": ("diagnosis_root_cause", "故障诊断与根因分析"),
    "06": ("dynamic_multimode", "动态、多工况与非平稳过程"),
    "07": ("quality_soft_sensor", "质量相关监控与软测量"),
    "08": ("batch_process", "批次过程监控"),
    "09": ("hybrid_digital_twin", "机理融合、数字孪生与过程建模"),
    "10": ("foundation_llm_multimodal", "工业大模型与多模态监控"),
    "11": ("datasets_benchmarks", "数据集、基准与评测方法"),
    "12": ("industrial_applications", "工业应用"),
    "13": ("university_courses", "著名大学课程教材与讲义"),
    "14": ("books_references", "教科书、专著与参考书"),
}

INTERVAL = {"arxiv.org": 5.0, "api.crossref.org": 1.5, "doaj.org": 1.5,
            "www.ebi.ac.uk": 1.5, "europepmc.org": 2.0, "api.opencitations.net": 2.0}

STOP = {"a", "an", "the", "of", "for", "and", "in", "on", "with", "to", "via", "by", "is", "are",
        "from", "at", "as", "its", "do", "how", "can", "using", "based", "towards", "toward", "under"}


def cat_dir(cat):
    slug, _ = CATS[cat]
    return f"{cat}_{slug}"


def host_key(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    return "arxiv.org" if host.endswith("arxiv.org") else host


def wait(key, interval):
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK_DIR / re.sub(r"[^A-Za-z0-9._-]", "_", key), "a+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        raw = f.read().strip()
        delay = interval - (time.time() - (float(raw) if raw else 0.0))
        if delay > 0:
            time.sleep(delay)
        f.seek(0)
        f.truncate()
        f.write(str(time.time()))


def http(url, accept="*/*", timeout=90, tries=3, headers=None, max_bytes=300_000_000):
    """Return (status, body_bytes, final_url, content_type)."""
    key = host_key(url)
    err = ""
    for attempt in range(tries):
        wait(key, INTERVAL.get(key, 3.0))
        try:
            h = {"User-Agent": UA, "Accept": accept, **(headers or {})}
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read(max_bytes), r.geturl(), r.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
            if e.code == 429:
                time.sleep(30 * (attempt + 1))
                continue
            if 400 <= e.code < 500:
                return e.code, b"", url, ""
        except Exception as e:  # network error / timeout
            err = repr(e)[:200]
        time.sleep(6 * (attempt + 1))
    return None, err.encode(), url, ""


def get_json(url, **kw):
    st, body, _, _ = http(url, accept="application/json", **kw)
    if st != 200:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return None


def fold(s):
    s = re.sub(r"[{}\\$]", "", s or "")
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "")


def norm(s):
    """Title key for dedup: lower-case ASCII alnum, CJK kept."""
    s = unicodedata.normalize("NFKC", strip_tags(s or "")).lower()
    return "".join(ch for ch in s if ch.isalnum())


def has_cjk(s):
    return any("一" <= ch <= "鿿" for ch in s or "")


def tokens(s):
    return [t for t in re.findall(r"[a-z0-9]+", fold(strip_tags(s)).lower()) if t not in STOP and len(t) > 1]


def title_similarity(a, b):
    if has_cjk(a) or has_cjk(b):
        ca, cb = set(norm(a)), set(norm(b))
        return len(ca & cb) / max(1, len(ca | cb))
    ta, tb = set(tokens(a)), set(tokens(b))
    return len(ta & tb) / max(1, len(ta | tb))


def title_in_text(title, text):
    """Fraction of title tokens (or CJK characters) present in text, whitespace-insensitive."""
    if has_cjk(title):
        tt = [c for c in norm(title) if "一" <= c <= "鿿"]
        blob = norm(text)
        return sum(1 for c in tt if c in blob) / len(tt) if tt else 0.0
    tt = tokens(title)
    blob = re.sub(r"[^a-z0-9]", "", fold(text).lower())
    return sum(1 for t in tt if t in blob) / len(tt) if tt else 0.0


def surname(name):
    name = (name or "").strip()
    if has_cjk(name):
        return name[:1]
    if "," in name:
        name = name.split(",")[0]
        parts = fold(name).split()
    else:
        parts = fold(name).split()
    return re.sub(r"[^A-Za-z]", "", parts[-1]) if parts else "Anon"


def short_title(title, n=4):
    title = fold(strip_tags(title))
    head = title.split(":")[0].strip()
    if ":" in title and 1 <= len(head.split()) <= 3:
        words = re.findall(r"[A-Za-z0-9]+", head)
    else:
        words = [w for w in re.findall(r"[A-Za-z0-9]+", title) if w.lower() not in STOP][:n]
    return "".join(w[:1].upper() + w[1:] for w in words)[:40] or "Untitled"


def window_status(date):
    """date is YYYY, YYYY-MM or YYYY-MM-DD."""
    if not date:
        return "待核实"
    lo = (date + "-01-01")[:10]
    hi = (date + "-12-31")[:10] if len(date) == 4 else (date + "-31")[:10]
    # an item found on the search date was public by then, so the upper bound is the search date
    if lo >= WINDOW_START and min(hi, WINDOW_END) <= WINDOW_END:
        return "近三年"
    if hi < WINDOW_START:
        return "三年前"
    return "待核实（日期精度不足）"


def load(path, default):
    path = Path(path)
    return json.loads(path.read_text()) if path.exists() else default


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
    os.replace(tmp, path)


def append_jsonl(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
