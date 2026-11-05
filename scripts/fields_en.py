"""Full-text keyword evidence for verified papers (automatic, not a reading of the paper).

  python3 -I scripts/fields_en.py

For every verified paper with cached extracted text (WORK/text/<sid>.txt.gz) record which benchmark /
dataset names, Tennessee Eastman version cues, metric names, point-adjust wording, random-split wording
and code links occur in the full text, with a short context snippet. Output: state/fulltext_fields_en.json.
These are keyword hits only; the catalog labels them "全文关键词自动检出，未人工核读".
"""
import gzip
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import STATE, WORK, load, save  # noqa: E402

BENCH = {
    "Tennessee Eastman": r"tennessee[\s-]*eastman",
    "TE 修订版/扩展数据（Bathelt/Ricker/Reinartz/Rieth 等）": r"bathelt|reinartz|rieth|revised\s+(te|tennessee)|extended\s+tennessee|ricker",
    "青霉素发酵仿真（PenSim/IndPenSim）": r"pensim|indpensim|penicillin",
    "CSTR 仿真": r"\bcstr\b|continuous[\s-]*stirred[\s-]*tank",
    "三相流装置（Cranfield）": r"three[\s-]*phase\s+flow|cranfield",
    "脱丁烷塔数据": r"debutani[sz]er",
    "硫回收装置数据": r"sulfur\s+recovery|sulphur\s+recovery",
    "DAMADICS": r"damadics",
    "SKAB": r"\bskab\b",
    "SWaT/WADI（网络安全测试台）": r"\bswat\b|\bwadi\b",
    "TCLab": r"tclab",
    "高炉": r"blast\s+furnace",
    "污水处理基准（BSM1/BSM2）": r"\bbsm[12]\b|benchmark\s+simulation\s+model",
    "半导体刻蚀/晶圆数据": r"\betch|wafer",
    "Fed-batch/发酵": r"fed[\s-]*batch|fermentation",
}
METRICS = {
    "误报率 FAR": r"false\s+alarm\s+rate|\bFAR\b",
    "检测率 FDR": r"fault\s+detection\s+rate|detection\s+rate|\bFDR\b",
    "漏报率 MDR": r"missed\s+detection|miss(ed)?\s+alarm|\bMDR\b",
    "检测延迟": r"detection\s+delay|detection\s+time|time\s+to\s+detect",
    "F1": r"\bF1\b|f1[\s-]*score",
    "AUC/ROC": r"\bAUC\b|\bROC\b",
    "准确率": r"\baccuracy\b",
    "RMSE": r"\bRMSE\b",
    "R²": r"\bR\s*\^?\s*2\b|R-squared|coefficient\s+of\s+determination",
    "ARL（平均运行长度）": r"average\s+run\s+length|\bARL\b",
}
POINT_ADJ = r"point[\s-]*adjust|point[\s-]*wise\s+adjust|adjusted\s+f1"
RANDOM_SPLIT = r"randomly\s+(split|divided|partitioned|selected)|random\s+(split|shuffle|partition)|shuffl"
CODE = r"https?://(?:www\.)?(?:github\.com|gitlab\.com|zenodo\.org|codeocean\.com|figshare\.com)/[^\s\)\]\},;]+"


def snippet(text, m, w=60):
    a, b = max(0, m.start() - w), min(len(text), m.end() + w)
    return " ".join(text[a:b].split())


def analyse(text):
    body = re.split(r"\n\s*(references|bibliography|参考文献)\s*\n", text, flags=re.I)[0]
    out = {"benchmarks": {}, "metrics": [], "point_adjust": "", "random_split": "", "code_links": []}
    for name, rx in BENCH.items():
        ms = list(re.finditer(rx, body, re.I))
        if ms:
            out["benchmarks"][name] = {"n": len(ms), "ctx": snippet(body, ms[0])}
    out["metrics"] = [k for k, rx in METRICS.items() if re.search(rx, body, re.I if k not in ("F1",) else 0)]
    m = re.search(POINT_ADJ, body, re.I)
    if m:
        out["point_adjust"] = snippet(body, m)
    m = re.search(RANDOM_SPLIT, body, re.I)
    if m:
        out["random_split"] = snippet(body, m)
    out["code_links"] = sorted(set(x.rstrip(".") for x in re.findall(CODE, text)))[:5]
    return out


def main():
    reg = load(STATE / "registry_en.json", {})
    res = load(STATE / "fulltext_fields_en.json", {})
    n = 0
    for sid, r in reg.items():
        if r.get("status") != "verified" or sid in res:
            continue
        p = WORK / "text" / f"{sid}.txt.gz"
        if not p.exists():
            continue
        with gzip.open(p, "rt") as f:
            res[sid] = analyse(f.read())
        n += 1
    save(STATE / "fulltext_fields_en.json", res)
    print("analysed", n, "total", len(res))


if __name__ == "__main__":
    main()
