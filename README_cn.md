# 工业过程监控文献库（恢复版）

这个仓库恢复自一个已无法访问的旧仓库。**恢复并不完整：旧版的论文清单和论文 PDF 都没有找回。** 请先看下面的状态表。

## 恢复状态

| 内容 | 旧版 | 现在 |
|---|---|---|
| 论文和其他 PDF | 约 650 个 | 未恢复 |
| 书籍 | 24 种（约 31 个文件） | 3 种在 Release，21 种只有链接 |
| 旧版就未发布的书 | 2 种 | 只有链接 |
| 大学课程包 | 20 个 ZIP | 19 个在 Release，1 个因版权只有链接 |
| 目录 `catalog_cn.csv`、校验文件、阅读地图、检索日志 | 有 | 未找回 |
| 14 个分类索引 `domains/` | 有 | 未找回 |
| 脚本 | 13 个 Python 脚本和种子数据 | 找回 10 个脚本，种子数据未找回 |
| 下载失败清单、未发布清单 | 有 | 原样找回 |

- [`restored_files_cn.csv`](restored_files_cn.csv)：现有每个文件的状态、许可、来源和 SHA-256。
- [`lost_files_cn.csv`](lost_files_cn.csv)：旧分支里没有找回的文件，以及它们的大小和 git blob 哈希。
- [`download_failures_cn.csv`](download_failures_cn.csv)：旧版记录的下载失败条目。这些文件旧版本来就没有。

## 文件在哪里

全文在 Release [`ipm-restored-20261105`](https://github.com/yuriev315/industrial-process-monitoring-literature/releases/tag/ipm-restored-20261105) 的 tar 包里，解压后是 `books/` 和 `university_materials/`。

```bash
tar -xf industrial_process_monitoring_literature_20261105_restored_cn_en.tar
```

仓库中的 `*.url.txt` 是占位文件，写明标题、官方地址和没有收录的原因。它们分三种：

- **版权受限：** 没有查到再分发许可，或许可仅限个人使用。请到官方地址下载。
- **开放获取但未收录：** 8 本 Springer 书。许可允许再分发，但出版社网站拦截了脚本下载，可以用浏览器下载。
- **地址失效：** NIST/SEMATECH 手册的章节 PDF 已不在预期地址，保留手册主页链接。

## 内容来源和可靠性

- **原样找回的 12 个文件：** git blob 哈希与旧仓库记录完全一致。
- **重新下载的书和课程包：** 来自官方地址。旧校验文件已丢失，无法逐字节比较，内容可能是更新后的版本。
- **Notre Dame 课程网站：** 是重新抓取后打包的，与旧版不是同一次抓取。

## 脚本

`scripts/` 里的脚本不能单独运行。`discover_en.py`、`seedcheck_en.py`、`pmcmap_en.py` 以及 `scripts/seeds/`、`scripts/state/`、`scripts/cache/` 都没有找回。保留这些脚本是为了记录旧流程。

## 许可

各文件的许可见 `restored_files_cn.csv`。

- MIT OpenCourseWare 课程包：CC BY-NC-SA 4.0，版权归 MIT 及相关作者所有，仅限非商业使用。
- Murphy《Probabilistic Machine Learning》两卷：CC BY-NC-ND 4.0。
- Dunn《Process Improvement Using Data》：CC BY-SA 4.0。
- Notre Dame CBE 30338：文字 CC BY-NC-ND 4.0，代码 MIT。

这个仓库的脚本没有单独声明许可证。
