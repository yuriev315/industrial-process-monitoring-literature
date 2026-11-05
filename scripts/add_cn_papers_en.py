"""Append the hand-screened Chinese papers from 自动化学报 (scan: cnjournal_en.py) to category seeds.
Annotations are written from the journal's Chinese abstracts. Idempotent (skips keys already present).

  python3 -I scripts/add_cn_papers_en.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_en import CATS, SEEDS  # noqa: E402


def A(**k):
    base = dict(industry="待全文核实", process="待全文核实", task="检测", process_type="待全文核实", method="",
                mechanism="待全文核实", data_source="待全文核实", datasets="待全文核实", data_public="待全文核实",
                code="摘要未提及，待全文核实", modes="待全文核实", fault_types="待全文核实", labels="待全文核实",
                online="待全文核实", split="待全文核实", fault_data_for_tuning="待全文核实", metrics="待全文核实",
                point_adjust="不适用", summary="", basis="摘要（期刊官网中文摘要）")
    base.update(k)
    return base


E = {
    "02": [("c230154", "慢特征分析", "分布式动态慢特征分析用于大型工业过程运行状态评价，代表中文期刊中的分布式动态潜变量方法",
            A(industry="待全文核实（摘要称工业过程案例）", task="运行状态评价（非优状态识别）", process_type="连续",
              method="DTW+K-medoids 过程分解；分块动态 SFA；贝叶斯推理融合全局指标", data_source="仿真+工业案例（摘要截断，待全文核实）",
              summary="作者提出分布式动态 SFA 运行状态评价方法：用 DTW 与 K-medoids 分解过程，各子块建立动态 SFA 模型，再以贝叶斯推理得到全局评价指标；摘要称在数值案例与工业过程上验证。")),
           ("c250134", "慢特征分析", "以独立慢特征分析改进动态过程中 ICA 的白化步骤，代表 ICA 与 SFA 融合的监控统计方法",
            A(industry="未涉及具体行业（方法研究）", process="数值仿真与电动伺服机构实验", method="独立慢特征分析（ISFA）：双目标优化、牛顿迭代、EWMA 修正统计量与综合指标",
              data_source="仿真+实验装置", datasets="数值仿真；电动伺服机构实验",
              summary="作者提出 ISFA，以原始观测与白化矩阵构造双目标优化，替代 PCA 白化以适应动态过程，并用 EWMA 修正统计量构建综合检测指标；摘要称在数值仿真与电动伺服机构实验上验证。"))],
    "03": [("c250617", "知识蒸馏/表示学习", "以多教师知识蒸馏把 KPCA 与 ICA 知识统一到自编码器，并在合成氨实际过程验证",
            A(industry="化工（合成氨）；TE 仿真", process="田纳西-伊斯曼过程；合成氨实际过程", process_type="连续",
              method="两阶段多教师知识蒸馏（KPCA、ICA 教师 → 学生自编码器），特征层与重构层蒸馏", data_source="仿真+真实工业",
              datasets="TEP（版本待全文核实）；合成氨过程数据（是否公开待全文核实）",
              summary="作者将核 PCA 与 ICA 提取的异构知识通过两阶段蒸馏内化到学生自编码器，实现非线性与非高斯特征统一建模；摘要称在 TE 仿真与合成氨实际过程上验证。"))],
    "05": [("c240151", "故障传播路径", "以故障源图与图匹配刻画不同故障传播路径的差异，用于工业过程故障诊断",
            A(task="诊断", method="故障传播路径感知网络 FPPAN：k-NN 与剪枝 k 跳可达路径构建故障源图，图匹配分类",
              summary="作者从故障源邻域关系与故障传播两个角度构建“故障源图”，将基于特征的分类转为基于结构关系的图匹配；摘要未给出数据集名称。")),
           ("c250108", "因果发现与因果诊断", "跨时空稳定因果动态贝叶斯网络用于工业过程异常工况定位与控制推理",
            A(task="根因定位/异常工况定位与安全控制", method="稳定学习 + 动态贝叶斯网络（滞后节点）+ 信息熵筛选 + 协变量平衡重加权",
              modes="12 种典型工况案例（摘要）",
              summary="作者用稳定学习挖掘不同时空分布下一致的因果特征，以动态贝叶斯网络刻画滞后依赖，并以样本重加权减少虚假因果；摘要称选取 12 种典型工况案例验证。"))],
    "06": [("c230156", "多工况与工况识别", "利用多模态（多工况）过程共性与个性特征进行故障等级评估",
            A(task="故障等级评估", method="共性-个性深度置信网络（CS-DBN）+ 加权逻辑回归", modes="多模态（多工况）过程，数量待全文核实",
              labels="使用已知故障等级数据（摘要）",
              summary="作者提出 CS-DBN，度量多工况数据分布的相似与差异以提取共性与个性特征，再构建故障等级评估模型，以缓解单一工况故障信息不足问题。"))],
    "07": [("c240627", "质量相关故障检测", "在质量变量不可测时以质量关联虚拟变量划分质量相关变量并做 ICA 故障检测",
            A(task="质量相关故障检测", method="质量关联虚拟变量（QRV）+ 假设检验变量划分 + ICA", labels="质量变量不可测场景（摘要）",
              summary="作者构造质量关联虚拟变量间接反映质量特性，据此用假设检验划分质量相关变量，再建立 ICA 质量相关故障检测模型。")),
           ("c250725", "软测量建模", "研究深度学习软测量的对抗鲁棒性，提出对抗训练与攻击检测融合的防御方法",
            A(task="软测量（鲁棒性）", method="对抗训练（SPAS-FAAT）+ 大扰动攻击检测融合（ATADI）",
              summary="作者指出深度学习软测量易受微小扰动对抗样本攻击，提出仅以小扰动样本做特征锚定式对抗训练、并以检测器拦截大扰动样本的融合防御方法。"))],
    "09": [("c230457", "状态估计", "综述深度学习与贝叶斯滤波（深度卡尔曼滤波、自适应卡尔曼滤波）的融合，支撑过程状态估计",
            A(task="综述（状态估计）", process_type="不适用", method="综述：深度卡尔曼滤波、融合深度学习的自适应卡尔曼滤波",
              mechanism="机理融合：状态空间模型与深度学习结合", data_source="不适用", datasets="不适用",
              summary="作者梳理不同领域融合深度学习的贝叶斯滤波应用，将不确定性问题归纳为特征提取与参数辨识两类，并总结深度卡尔曼滤波等两类结合方法。"))],
    "12": [("c240660", "钢铁与冶金", "高炉炼铁过程故障检测与诊断的中文综述（近 20 年数据驱动方法）",
            A(industry="钢铁与冶金", process="高炉炼铁", task="综述（检测与诊断）", process_type="连续", method="综述：按数据量需求分类的数据驱动方法",
              data_source="不适用", datasets="不适用",
              summary="作者总结近 20 年高炉炼铁过程数据驱动故障检测与诊断研究，按数据量需求分类分析方法优劣并提出发展趋势。")),
           ("c230674", "钢铁与冶金", "利用工业内窥镜料面视频识别高炉异常状态，代表图像信息在过程监控中的应用",
            A(industry="钢铁与冶金", process="高炉（料面煤气流）", task="异常状态识别", process_type="连续",
              method="多尺度纹理模糊 C 均值提取煤气流区域 + 特征编码降维 + 自适应 K-means++", data_source="真实工业（工业内窥镜视频，摘要）",
              summary="作者基于高炉料面视频图像提取高温煤气流区域与多元特征，实现高炉异常状态的感知与识别。")),
           ("c240378", "钢铁与冶金", "红外与可见光协同在线检测高炉铁口铁水温度场，属难测质量变量的在线测量",
            A(industry="钢铁与冶金", process="高炉出铁（铁口铁水温度场）", task="质量相关变量在线检测", process_type="连续",
              method="红外-可见光视觉测温；粉尘透射率估计（色彩一致性、雾线先验）", data_source="真实工业（摘要称设计测温系统，待全文核实）",
              summary="作者设计红外与可见光协同测温系统，以可见光图像估计粉尘透射率并校正红外测温，实现铁水温度场在线检测。")),
           ("c230272", "矿物加工/有色", "可解释的电熔镁炉异常工况识别，代表有色冶金过程的工况监控",
            A(industry="有色冶金（电熔镁）", process="电熔镁炉", task="异常工况识别", method="深层卷积随机配置网络（DCSCN），可解释性评测",
              summary="作者提出深层卷积随机配置网络用于电熔镁炉异常工况识别，并定义可解释性可信度指标以自适应调整网络层级。")),
           ("c250596", "电力", "烟气脱硫系统运行状态预测与故障模式推理（实际系统数据）",
            A(industry="电力（烟气脱硫）", process="烟气脱硫系统循环泵", task="预警（运行状态预测）", process_type="连续",
              method="深度模糊推理模型（深度模糊信念网络 + 推理门控层）", data_source="真实工业（摘要称实际烟气脱硫系统）",
              summary="作者提出深度模糊推理模型预测烟气脱硫设备运行状态并识别故障模式，以实际系统循环泵浆液 pH 等数据验证。"))],
}
LEVEL = {"c250596": "设备层（与生产过程结合）", "c250134": "基础方法", "c230457": "基础方法"}
REVIEW = {"c240660", "c230457"}

for cat, items in E.items():
    p = SEEDS / f"{cat}_{CATS[cat][0]}_seed_cn.json"
    s = json.load(open(p))
    n = max(int(x["sid"].split("-")[1]) for x in s)
    have = {x.get("key") for x in s}
    for d, sub, reason, ann in items:
        key = "doi:10.16383/j.aas." + d
        if key in have:
            continue
        n += 1
        s.append(dict(sid=f"{cat}-{n:03d}", key=key, type="综述" if d in REVIEW else "原始研究", subtopic=sub, priority="中",
                      reason=reason + "（中文期刊，补充中文文献）", cross=[], reserve=False, level=LEVEL.get(d, "过程层"), ann=ann))
    json.dump(s, open(p, "w"), ensure_ascii=False, indent=1)
    print(cat, len(s))
