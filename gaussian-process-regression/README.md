# 高斯过程回归：稳健 GP（RCGP）资料与离线环境

本文件夹围绕论文 *Robust and Conjugate Gaussian Process Regression*（Altamirano, Briol, Knoblauch, ICML 2024, [arXiv:2311.00463](https://arxiv.org/abs/2311.00463)），收集论文、作者代码、相关稳健 GP 代码、GPflow 文档、UCI 回归数据，以及一套 Windows x64 离线运行环境（Python 3.10.11 / TensorFlow 2.13.0 / GPflow 2.9.1）。

## 目录

| 路径 | 内容 | 许可 |
| --- | --- | --- |
| `2311.00463v2.pdf.url` | RCGP 论文 v2 的下载链接 | arXiv 默认许可，不再分发 |
| `RCGP-main/` | 作者代码 [maltamiranomontero/RCGP](https://github.com/maltamiranomontero/RCGP)（提交 `aff281a`）：`rcgp/` 实现、`experiments/` 笔记本与 UCI 基准、Flash crash 数据、图和结果 | 上游没有许可证，逐个文件给 `.url` 链接 |
| `Robust-Scalable-GPR-main.zip` | [YifanLu2000/Robust-Scalable-GPR](https://github.com/YifanLu2000/Robust-Scalable-GPR) 源码 | Apache-2.0 |
| `GPflow-docs.zip` | GPflow 2.9.1 HTML 文档（解压后打开 `GPflow-docs/index.html`） | Apache-2.0 |
| `data/` | Boston（原版与修正版）、Concrete、Energy efficiency、Yacht 数据 | UCI 数据 CC BY 4.0；Boston 见说明文件 |
| `yacht+hydrodynamics.zip` | UCI Yacht 原始压缩包 | CC BY 4.0 |
| `offline-RCGP/` | 离线环境：锁定的依赖、安装与测试脚本、实验数据缓存、GPflow `benchmark` 工具包 | 自有脚本；`vendor/benchmark` 为 Apache-2.0 |
| `FILES.csv` | 全部文件的路径、类型、许可、来源、大小和 SHA-256 | |

## `.url` 占位文件

没有再分发许可的文件以同名 `.url` 文件给出，例如 `RCGP-main/rcgp/rcgp.py.url`。文件是 Windows 快捷方式格式，双击即可打开下载地址；`[File]` 段写明文件名、字节数、SHA-256 和许可情况。

联网时一次性下载并校验全部占位文件：

```powershell
python offline-RCGP\scripts\fetch_url_files.py            # 全部
python offline-RCGP\scripts\fetch_url_files.py RCGP-main  # 只下载 RCGP 代码
```

脚本只保留大小和 SHA-256 都一致的文件。

## 离线环境

Release 附件（与本文件夹同一个 Release）：

| 附件 | 解压后位置 | 内容 |
| --- | --- | --- |
| `gaussian-process-regression.zip` | `gaussian-process-regression/` | 本文件夹 |
| `offline-RCGP-python-3.10.11.zip` | `gaussian-process-regression/offline-RCGP/python/` | Python 3.10.11 安装包与嵌入式包（含 python.org 签名），VC++ 运行库链接 |
| `offline-RCGP-wheels-py310.zip` | `gaussian-process-regression/offline-RCGP/wheels/` | 154 个 Windows cp310 wheel；`tensorflow_intel` 2.13.0（264 MiB）为 `.url` |

三个 zip 解压到同一个父目录即可合并。之后按 [`offline-RCGP/README.md`](offline-RCGP/README.md) 安装和测试。

## 参考

- M. Altamirano, F.-X. Briol, J. Knoblauch. Robust and Conjugate Gaussian Process Regression. ICML 2024. arXiv:2311.00463.
- C. E. Rasmussen, C. K. I. Williams. *Gaussian Processes for Machine Learning*. MIT Press, 2006. <https://gaussianprocess.org/gpml/>
- GPflow: <https://github.com/GPflow/GPflow>
