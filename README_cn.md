# 工业过程监控文献库

工业过程监控方向的论文、书籍和大学课程资料，分 14 类整理。论文以 2023-10-29 至 2026-11-06 首次公开的开放获取文献为主。

## 规模

| 类型 | 条目 | 全文在 Release | 只有链接 |
|---|--:|--:|--:|
| 论文（01–12 类） | 442 | 380 | 62 |
| 大学课程资料（13 类） | 23 | 19 | 4 |
| 书籍（14 类） | 26 | 3 | 23 |

## 分类

| 编号 | 类别 | 索引 |
|---|---|---|
| 01 | 工业过程监控基础与综述 | [domains/01_fundamentals_reviews](domains/01_fundamentals_reviews/README_cn.md) |
| 02 | 统计与潜变量方法 | [domains/02_statistical_latent](domains/02_statistical_latent/README_cn.md) |
| 03 | 机器学习与深度学习监控 | [domains/03_ml_dl_monitoring](domains/03_ml_dl_monitoring/README_cn.md) |
| 04 | 异常检测与早期故障检测 | [domains/04_anomaly_incipient](domains/04_anomaly_incipient/README_cn.md) |
| 05 | 故障诊断与根因分析 | [domains/05_diagnosis_root_cause](domains/05_diagnosis_root_cause/README_cn.md) |
| 06 | 动态、多工况与非平稳过程 | [domains/06_dynamic_multimode](domains/06_dynamic_multimode/README_cn.md) |
| 07 | 质量相关监控与软测量 | [domains/07_quality_soft_sensor](domains/07_quality_soft_sensor/README_cn.md) |
| 08 | 批次过程监控 | [domains/08_batch_process](domains/08_batch_process/README_cn.md) |
| 09 | 机理融合、数字孪生与过程建模 | [domains/09_hybrid_digital_twin](domains/09_hybrid_digital_twin/README_cn.md) |
| 10 | 工业大模型与多模态监控 | [domains/10_foundation_llm_multimodal](domains/10_foundation_llm_multimodal/README_cn.md) |
| 11 | 数据集、基准与评测方法 | [domains/11_datasets_benchmarks](domains/11_datasets_benchmarks/README_cn.md) |
| 12 | 工业应用 | [domains/12_industrial_applications](domains/12_industrial_applications/README_cn.md) |
| 13 | 著名大学课程教材与讲义 | [domains/13_university_courses](domains/13_university_courses/README_cn.md) |
| 14 | 书籍与参考资料 | [domains/14_books_references](domains/14_books_references/README_cn.md) |

## 文件

| 文件 | 内容 |
|---|---|
| [`catalog_cn.csv`](catalog_cn.csv) | 全部条目：编号、标题、作者、首次公开日期、DOI/arXiv/PMCID、原始页面、全文地址、本地路径、许可证、全文位置、SHA-256 |
| [`archive_index_cn.csv`](archive_index_cn.csv) | 每个文件在哪个 tar 包里 |
| [`checksums_en.sha256`](checksums_en.sha256) | Release 中全部文件的 SHA-256 |
| [`release_excluded_cn.csv`](release_excluded_cn.csv) | 只有链接的条目及原因 |
| [`download_failures_cn.csv`](download_failures_cn.csv) | 未能下载的条目 |
| [`search_log_cn.md`](search_log_cn.md) | 检索平台、日期和全部检索式 |
| `scripts/screening_rules_cn.md` | 分类定义、纳入与排除规则 |

## 下载全文

全文在 Release [`ipm-full-20261106`](https://github.com/yuriev315/industrial-process-monitoring-literature/releases/tag/ipm-full-20261106) 的 2 个 tar 包中。把它们解压到同一目录，就能得到与 `catalog_cn.csv` 中“本地相对路径”一致的目录结构。

```bash
tar -xf industrial_process_monitoring_literature_20261106_batch001_cn_en.tar
tar -xf industrial_process_monitoring_literature_20261106_batch002_cn_en.tar
sha256sum -c checksums_en.sha256
```

## 收录规则

- **来源：** 论文来自 arXiv 和 PMC 开放获取数据集；书籍和课程资料来自作者或学校的官方页面。
- **全文：** 只有许可证明确允许再分发（CC 系列、公共领域）的文件才放进 Release。
- **只有链接：** 其余条目只放 `*.url.txt` 链接文件，写明标题、官方地址和原因。
- **筛选：** 按 `scripts/screening_rules_cn.md` 的规则用关键词自动筛选。分类是按标题和摘要的关键词判断的，没有逐篇人工通读，个别条目的归类可能不准确。

## 脚本

- `tools/`：检索、筛选、下载、校验和生成目录的脚本，需要 Python 3 和 `pypdf`。
- `scripts/`：另一套文献采集与整理脚本和筛选规则，缺少种子数据，不能单独运行。

## 许可

各条目的许可证见 `catalog_cn.csv`。使用时请遵守原许可，尤其是 NC（非商业）和 ND（禁止演绎）条款。

- MIT OpenCourseWare 课程包：CC BY-NC-SA 4.0。
- Murphy《Probabilistic Machine Learning》两卷：CC BY-NC-ND 4.0。
- Dunn《Process Improvement Using Data》：CC BY-SA 4.0。

本仓库的脚本没有单独声明许可证。
