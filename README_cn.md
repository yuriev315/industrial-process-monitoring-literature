# 工业过程监控文献库

工业过程监控方向的书籍、大学课程包和文献采集脚本。论文 PDF 目前不在本仓库中。

## 内容

| 内容 | 位置 |
|---|---|
| 书籍 3 种（全文） | Release 的 tar 包，`books/` |
| 大学课程包 19 个（全文） | Release 的 tar 包，`university_materials/` |
| 其他 23 种书和 1 个课程包 | 仓库里的 `*.url.txt` 链接文件 |
| 文献采集与整理脚本 | `scripts/` |
| 下载失败清单 | [`download_failures_cn.csv`](download_failures_cn.csv) |
| 仅限个人使用、未收录的书 | [`release_excluded_cn.csv`](release_excluded_cn.csv) |
| 逐文件状态、许可、来源和 SHA-256 | [`restored_files_cn.csv`](restored_files_cn.csv) |
| 未收录文件的路径、大小和 git blob 哈希 | [`lost_files_cn.csv`](lost_files_cn.csv) |

全文包在 Release [`ipm-restored-20261105`](https://github.com/yuriev315/industrial-process-monitoring-literature/releases/tag/ipm-restored-20261105)：

```bash
tar -xf industrial_process_monitoring_literature_20261105_restored_cn_en.tar
```

## 链接文件

`*.url.txt` 写明标题、官方地址和未收录的原因，分三种：

- **版权受限：** 没有查到再分发许可，或许可仅限个人使用。请到官方地址下载。
- **开放获取但未收录：** 8 本 Springer 书。许可允许再分发，但出版社网站拦截了脚本下载，可以用浏览器下载。
- **地址失效：** NIST/SEMATECH 手册的章节 PDF 已不在原地址，只保留手册主页链接。

## 脚本

`scripts/` 中缺少 `discover_en.py`、`pmcmap_en.py`、`reading_route_cn.md` 以及 `scripts/seeds/`、`scripts/state/`、`scripts/cache/`，所以这些脚本不能直接运行。

## 许可

各文件的许可见 `restored_files_cn.csv`。

- MIT OpenCourseWare 课程包：CC BY-NC-SA 4.0，版权归 MIT 及相关作者所有，仅限非商业使用。
- Murphy《Probabilistic Machine Learning》两卷：CC BY-NC-ND 4.0。
- Dunn《Process Improvement Using Data》：CC BY-SA 4.0。
- Notre Dame CBE 30338：文字 CC BY-NC-ND 4.0，代码 MIT。

脚本没有单独声明许可证。
