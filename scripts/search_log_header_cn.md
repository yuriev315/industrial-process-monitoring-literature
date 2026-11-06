# 检索日志（工业过程监控文献库）

- 检索执行日期：2026-10-29（UTC）。
- 近三年窗口：首次公开日期 2023-10-29 至 2026-10-29（检索日向前滚动三年）。
- 性质：范围检索，不是系统综述，不宣称穷尽。
- 检索词以英文为主，覆盖任务要求的 14 个核心词（industrial process monitoring、multivariate statistical process monitoring、statistical process control、process fault detection and diagnosis、root cause analysis、quality-related monitoring、soft sensor、batch process monitoring、multimode process、nonstationary process、incipient fault、process drift、causal diagnosis、hybrid modeling）及其组合；中文检索词用于《自动化学报》目录筛选（过程监测、故障检测、故障诊断、软测量、质量预测、批次/间歇过程、多工况、根因、故障溯源、数字孪生、状态估计等）。

## 1. 平台与用途

| 平台 | 用途 | 本机可用性（2026-10-29 实测） |
|---|---|---|
| arXiv API | 带日期过滤的检索；元数据（v1 日期、最新版本、journal_ref、DOI、摘要）；全文 PDF | 可用（限速 ≥5 秒/次） |
| DOAJ 文章检索 API | 开放获取期刊论文发现（标题/摘要字段检索，年份过滤） | 可用 |
| Europe PMC REST | 开放获取论文发现（OPEN_ACCESS:y，FIRST_PDATE 过滤） | 检索可用；其 PDF 渲染接口返回 Cloudflare 验证页，未使用 |
| PMC 开放获取数据集（AWS `pmc-oa-opendata`，NIH 官方分发）+ NCBI ID Converter | 将候选 DOI 映射到 PMCID，从官方数据集取出版社版 PDF 与许可信息 | 可用 |
| HAL API | 法国开放存档（含大量 IFAC 会议论文作者存档全文）——用于发现 | 检索 API 可用；但全文下载地址（`/document`、`/file/*.pdf`）在下载阶段返回反机器人验证页（“Making sure you're not a bot!”），按要求不绕过，HAL 来源论文只有在 arXiv/出版社有合法副本时才计数 |
| Crossref REST | DOI 元数据（在线/印刷日期、渠道、卷期页、许可）；后向引文（参考文献表）；开放获取书籍发现 | 可用 |
| OpenCitations Index v2 | 前向引文（施引文献） | 可用 |
| IEEE Xplore stampPDF | IEEE 开放获取论文（如 IEEE Access）出版社版 PDF | 可用（仅开放获取文章返回 PDF） |
| 出版社落地页 `citation_pdf_url` | Springer/BMC、Nature、PLoS、Frontiers、IOP 等开放获取 PDF | 可用 |
| 《自动化学报》官网 | 中文论文目录与官网 PDF | 可用 |
| 作者/大学/机构官网、MIT OCW、GitHub/GitLab、Zenodo | 书籍与课程讲义 | 可用 |
| 通用网页搜索 | 仅用于发现候选与核对版本线索，不作为计数依据 | 可用 |
| OpenAlex | 计划用于引文与开放获取定位 | 本机所在 IP 的当日免费额度已被耗尽（返回 “Insufficient budget”），未使用；未替用户申请 API key |
| Semantic Scholar API | 计划用于渠道核验 | HTTP 429 限流，未使用 |
| DOAB / OAPEN | 开放获取图书目录 | 对本机 IP 返回 403（“You address is not allowed”），未使用 |
| MDPI、ScienceDirect、Wiley、Taylor & Francis、SAGE、AIP、部分 EDP 站点 | 出版社全文 | 对本机返回 403/访问拒绝。按要求不绕过；这些出版社的论文只有在 PMC 数据集、arXiv 或 HAL 存在合法副本时才收录 |

## 2. 流程

1. 按 12 个论文类别分别执行检索式（附录逐条记录），合并去重进入候选池（DOI / arXiv ID / 规范化标题）。
2. 对候选池批量映射 PMCID，并标注全文渠道；只在有合法开放全文渠道的候选中筛选。
3. 筛选：阅读标题与摘要，按 `scripts/screening_rules_cn.md` 的类别定义、范围边界和年份规则选入主列表与备选；每条记录写明选入理由、子方向、研究层级（过程层/设备层/基础方法）与依据摘要填写的领域字段。
4. 引文追踪：每类至少对一篇代表性综述或研究做前向（OpenCitations）与后向（Crossref 参考文献表）追踪，结果并入候选池（附录中平台为“引文追踪”的条目）。
5. 下载与核验：HTTP 200、`%PDF-` 文件头、pypdf 可解析、≥4 页、可抽取字符数下限、首两页标题词匹配 ≥0.8、第一作者姓氏出现、参考文献节存在、首页不是补充材料；仅软性检查不过的进入“待核验”，不计数。按 SHA256、DOI、arXiv ID、规范化标题去重；同一文献只在一个主分类计数。
6. 主列表失败时由同类备选按顺序递补，直到约 50 份或备选耗尽。

## 3. 主要排除原则（摘要）

- 业务流程挖掘中的 “predictive process monitoring”、医疗/公共卫生 SPC、社交网络监控、环境监测（未涉及生产过程）。
- 单台设备（轴承、电机、齿轮箱、电池、光伏、变压器、车辆）故障诊断，除非明确与生产过程监控结合（此时标注“设备层”）。
- 网络安全入侵检测（含 ICS/SCADA 攻击检测）不作为过程监控文献计数。
- 疑似掠夺性或质量明显不足的期刊。
- 只有摘要、只有补充材料、需要登录或付费的全文。
