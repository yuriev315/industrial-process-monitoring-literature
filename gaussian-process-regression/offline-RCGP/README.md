# offline-RCGP：RCGP 实验的 Windows 离线环境

目标平台：Windows 10/11 x64。版本：Python 3.10.11、TensorFlow 2.13.0（`tensorflow-intel`）、TensorFlow Probability 0.21.0、GPflow 2.9.1、NumPy 1.24.3。完整版本见 `requirements/freeze-py310.txt`（155 个包，带 SHA-256）。

## 目录

```
offline-RCGP/
  python/        Python 3.10.11 安装包、嵌入式包、VC++ 运行库（来自 Release 附件）
  wheels/        Windows cp310 wheel（来自 Release 附件）
  requirements/  requirements-rcgp.txt（直接依赖）、freeze-py310.txt（锁定版本与哈希）
  scripts/       install_offline.ps1、prepare_data.py、test_offline.py、download_wheels.py、fetch_url_files.py
  data/uci/      Boston、Concrete、Energy、Yacht 数据
  data/cache/    RCGP UCI 基准读取的缓存目录（每个数据集及其 _asymmetric/_focused/_uniform 变体）
  vendor/benchmark/  GPflow 2.9.1 的 benchmark 工具包（RCGP 实验依赖），Apache-2.0
```

## 准备（联网机器上做一次）

以下文件没有随附件分发，需要在联网时取得：

1. `wheels/tensorflow_intel-2.13.0-cp310-cp310-win_amd64.whl`（264 MiB）
2. `python/vc_redist.x64.exe`（Microsoft VC++ 2015–2022 运行库；已安装可跳过）
3. `../RCGP-main/` 下的作者代码（运行 RCGP 本身才需要）

```powershell
cd gaussian-process-regression
python offline-RCGP\scripts\fetch_url_files.py offline-RCGP RCGP-main
```

也可以用 `python offline-RCGP\scripts\download_wheels.py` 按锁文件重新下载全部 wheel（pip 会校验哈希，任何操作系统都可以运行）。

## 安装（离线）

```powershell
cd gaussian-process-regression\offline-RCGP
powershell -ExecutionPolicy Bypass -File .\scripts\install_offline.ps1
```

脚本依次：

1. 检查 VC++ 运行库，缺少时运行 `python\vc_redist.x64.exe`；
2. 没有 `python\py310\python.exe` 时，把 Python 3.10.11 静默安装到 `python\py310`（当前用户，不改 PATH）；
3. 创建 `.venv`，用 `pip install --no-index --require-hashes` 从 `wheels\` 安装锁定的全部包；
4. 运行 `prepare_data.py` 补齐 `data\cache`，再运行 `test_offline.py`。

## 测试内容

`test_offline.py` 检查：

- TensorFlow、TFP、GPflow、NumPy 的版本，以及 SciPy、pandas、scikit-learn、xlrd、openpyxl 等能否导入；
- 四个 UCI 文件用 RCGP 实验同样的读取方式读出，形状为 (506, 14)、(1030, 9)、(768, 9)、(308, 7)；
- 在 Yacht 数据上训练 GPflow GPR；
- 有 `../RCGP-main` 时：在含 10% 离群点的数据上训练 RCGPR（IMQ 权重函数），并导入 UCI 实验模块、从缓存读出数据集。

全部通过时退出码为 0。

## 运行 RCGP 实验

```powershell
cd ..\RCGP-main
$env:PYTHONPATH = "$PWD;$PWD\..\offline-RCGP\vendor"
..\offline-RCGP\.venv\Scripts\python.exe -m experiments.uci.run full experiments\uci\experiment_results --cache_dir ..\offline-RCGP\data\cache
```

UCI 基准在 `--cache_dir\data\<数据集>\` 找到文件时不会联网下载。笔记本（`experiments\*.ipynb`）可用 `.venv\Scripts\jupyter-lab.exe` 打开，内核同样需要上面的 `PYTHONPATH`。

`vendor/benchmark` 中 `metric_api.py`、`metrics.py`、`model_api.py`、`registry.py`、`sharding.py`、`tag.py` 与 GPflow v2.9.1 相同；`paths.py` 改为从 `experiments.uci.metadata` 读取运行信息，且在不允许符号链接的 Windows 上把 `latest` 写成文本文件；`dataset_api.py` 从 RCGP 实验代码导入数据类型。
