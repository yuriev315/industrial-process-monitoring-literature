"""Generate search_log_cn.md from state/search_log_en.jsonl (every executed query) plus the fixed
sections in scripts/search_log_header_cn.md (platforms, rules, exclusions written by hand).

  python3 -I scripts/build_searchlog_en.py
"""
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import CATS, ROOT, SCRIPTS, STATE  # noqa: E402

SRC = {"arxiv": "arXiv API", "doaj": "DOAJ 文章检索 API", "epmc": "Europe PMC REST（OPEN_ACCESS:y）",
       "crossref": "Crossref works", "hal": "HAL API（仅含全文）", "cite": "引文追踪（fwd=OpenCitations 施引；bwd=Crossref 参考文献）", "aas": "《自动化学报》官网目录"}


def main():
    log = [json.loads(l) for l in open(STATE / "search_log_en.jsonl")]
    head = (SCRIPTS / "search_log_header_cn.md").read_text() if (SCRIPTS / "search_log_header_cn.md").exists() else ""
    out = [head.rstrip(), "", "## 附录：逐条检索记录（脚本自动记录）", "",
           f"共 {len(log)} 条检索。日期过滤：arXiv 为 submittedDate ≥ 起始日；DOAJ/HAL 为年份 ≥ 起始年；"
           "Europe PMC 为 FIRST_PDATE ≥ 起始日；Crossref 为 from-pub-date ≥ 起始日；引文追踪 fwd 只保留施引记录创建日期 ≥ 起始月。"
           "“命中”为平台返回总数，“取回”为实际读取条数，“新增”为合并去重后新进入候选池的条数。", ""]
    by = collections.defaultdict(list)
    for x in log:
        by[x["cat"]].append(x)
    for cat in sorted(by):
        label = CATS[cat][1] if cat in CATS else "中文期刊（《自动化学报》目录筛选，结果分配到各类）"
        out += [f"### {cat} {label}", "", "| 编号 | 时间（UTC） | 平台 | 起始日 | 命中 | 取回 | 新增 | 检索式 |",
                "|---|---|---|---|---|---|---|---|"]
        for x in by[cat]:
            q = x["q"].replace("|", "\\|")
            out.append(f"| {x['qid']} | {x['time'][:16].replace('T', ' ')} | {SRC.get(x['src'], x['src'])} | {x.get('start', '')} "
                       f"| {x['total']} | {x['fetched']} | {x['new']} | `{q}` |")
        out.append("")
    (ROOT / "search_log_cn.md").write_text("\n".join(out) + "\n")
    print("queries", len(log))


if __name__ == "__main__":
    main()
