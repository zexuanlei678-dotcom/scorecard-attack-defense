# -*- coding: utf-8 -*-
"""生成正式期末报告 Word 文档（.docx）。

内容基于 docs/report.md，按中文学术报告规范排版：
A4、四边2.5cm；标题黑体、正文宋体、西文 Times New Roman；
正文小四、1.5倍行距、首行缩进2字符；含封面、目录域、图表题注、参考文献。
运行：python scripts/build_report_docx.py
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "互联网金融期末报告.docx"

BLACK = RGBColor(0, 0, 0)
HEI = "黑体"
SONG = "宋体"
KAI = "楷体"
TNR = "Times New Roman"


# ---------------- 基础工具 ----------------
def set_run(run, cn_font=SONG, size=12, bold=False, color=BLACK, en_font=TNR, italic=False):
    run.font.name = en_font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), cn_font)
    rfonts.set(qn("w:ascii"), en_font)
    rfonts.set(qn("w:hAnsi"), en_font)


def body_para(doc, text, indent=True, size=12):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    if indent:
        pf.first_line_indent = Pt(size * 2)
    r = p.add_run(text)
    set_run(r, size=size)
    return p


def heading(doc, text, level):
    sizes = {1: 16, 2: 14, 3: 12}
    p = doc.add_paragraph()
    p.style = doc.styles[f"Heading {level}"]
    pf = p.paragraph_format
    pf.space_before = Pt({1: 14, 2: 11, 3: 9}[level])
    pf.space_after = Pt({1: 6, 2: 5, 3: 4}[level])
    pf.keep_with_next = True
    r = p.add_run(text)
    set_run(r, cn_font=HEI, size=sizes[level], bold=True)
    return p


def add_field(paragraph, instr):
    fb = OxmlElement("w:fldChar"); fb.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    sep = OxmlElement("w:fldChar"); sep.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar"); end.set(qn("w:fldCharType"), "end")
    r = paragraph.add_run()
    r._r.append(fb); r._r.append(it); r._r.append(sep); r._r.append(end)
    return r


def add_figure(doc, img_name, caption, width_cm=14.5):
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(RESULTS / img_name), width=Cm(width_cm))
    c = doc.add_paragraph(); c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    c.paragraph_format.space_before = Pt(2); c.paragraph_format.space_after = Pt(8)
    r = c.add_run(caption)
    set_run(r, size=10.5)


def shade_cell(cell, color_hex):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:fill"), color_hex)
    tcpr.append(shd)


def make_table(doc, headers, rows, caption, col_widths=None):
    cap = doc.add_paragraph(); cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(8); cap.paragraph_format.space_after = Pt(2)
    r = cap.add_run(caption); set_run(r, size=10.5, bold=True)

    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = "Table Grid"
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        shade_cell(hdr[i], "D9D9D9")
        para = hdr[i].paragraphs[0]; para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rr = para.add_run(str(h)); set_run(rr, size=10.5, bold=True)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            para = cells[i].paragraphs[0]
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            rr = para.add_run(str(v)); set_run(rr, size=10.5)
    if col_widths:
        for i, w in enumerate(col_widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


# ---------------- 文档级设置 ----------------
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin = sec.bottom_margin = sec.left_margin = sec.right_margin = Cm(2.5)

normal = doc.styles["Normal"]
normal.font.name = TNR; normal.font.size = Pt(12)
normal.element.rPr.rFonts.set(qn("w:eastAsia"), SONG)

# 页脚页码
footer_p = sec.footer.paragraphs[0]; footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_field(footer_p, "PAGE")

# ---------------- 封面 ----------------
for _ in range(4):
    doc.add_paragraph()
tp = doc.add_paragraph(); tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
tr = tp.add_run("分数会说谎"); set_run(tr, cn_font=HEI, size=26, bold=True)
sp = doc.add_paragraph(); sp.alignment = WD_ALIGN_PARAGRAPH.CENTER
sr = sp.add_run("信用评分卡的特征操纵攻防研究"); set_run(sr, cn_font=HEI, size=18, bold=True)
ep = doc.add_paragraph(); ep.alignment = WD_ALIGN_PARAGRAPH.CENTER
er = ep.add_run("When Scores Lie: Feature Manipulation Attacks and Defenses in Credit Scorecards")
set_run(er, size=12, italic=True)
for _ in range(8):
    doc.add_paragraph()
gp = doc.add_paragraph(); gp.alignment = WD_ALIGN_PARAGRAPH.CENTER
gr = gp.add_run("互联网金融课程期末报告"); set_run(gr, cn_font=KAI, size=14)
doc.add_page_break()

# ---------------- 目录 ----------------
toc_title = doc.add_paragraph(); toc_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
tr2 = toc_title.add_run("目  录"); set_run(tr2, cn_font=HEI, size=16, bold=True)
toc_p = doc.add_paragraph()
add_field(toc_p, 'TOC \\o "1-2" \\h \\z \\u')
hint = doc.add_paragraph(); hr2 = hint.add_run("（打开文档后右键目录选择“更新域”即可显示页码）")
set_run(hr2, size=9, color=RGBColor(0x80, 0x80, 0x80))
doc.add_page_break()

# ---------------- 摘要 ----------------
heading(doc, "摘要", 1)
abstract = (
    "信用评分卡以可解释、可落地的优势成为消费信贷审批的事实标准，但其输入端混合了大量可被借款人"
    "短期改变的特征。本研究在Give Me Some Credit公开数据集（150000样本）上构建完整的WOE-逻辑回归"
    "评分卡（测试集AUC=0.858、KS=0.560），随后设计四类特征操纵算子模拟“资质包装”攻击。实验显示，"
    "强组合攻击可使46.1%的原被拒客户翻转通过，而这些客户的真实坏账率达9.92%，约为正常通过客户"
    "（1.09%）的9.1倍。研究进一步评估稳健评分卡、突变检测、对抗训练三类防御：剔除高可操纵特征的"
    "稳健卡将攻击翻转率压至6.6%且AUC仅损失0.031，性价比最优。UCI台湾信用卡数据集（30000样本）上的"
    "外部验证得到方向一致的结论，证明评分失真现象跨数据集稳健。"
)
body_para(doc, abstract)
kw = doc.add_paragraph(); kw.paragraph_format.space_before = Pt(6)
r1 = kw.add_run("关键词："); set_run(r1, cn_font=HEI, size=12, bold=True)
r2 = kw.add_run("信用评分卡；WOE编码；特征操纵；对抗机器学习；信贷风险"); set_run(r2, size=12)
doc.add_page_break()

# ---------------- 正文 ----------------
heading(doc, "一、引言", 1)
heading(doc, "1.1 研究背景", 2)
body_para(doc,
    "自FICO公司在20世纪50年代推出评分卡方法以来，以统计模型量化借款人信用风险已成为信贷业务的"
    "标准流程。评分卡将申请人的各类特征转换为可加分数，审批决策因此具备客观性、一致性与可解释性，"
    "并满足监管对模型透明性的要求。")
body_para(doc,
    "然而，评分卡的有效性建立在一个隐含前提上：输入特征真实反映借款人的长期信用状况。现实中，"
    "借款人存在明确的策略性操纵动机——申贷结果直接关系到资金可得性，而部分特征（如信用额度利用率、"
    "负债比率）可以通过账单日前突击还款、债务重组等方式在短期内显著改变。互联网上“申贷前如何养征信”"
    "的大量攻略表明，这类行为并非理论假设，而是普遍存在的实践。")
heading(doc, "1.2 问题提出", 2)
body_para(doc, "当特征可被操纵而模型仍按历史规律打分时，就会出现评分失真：操纵提升了评分，却没有改变借款人的真实违约倾向。本研究据此提出三个问题：")
body_para(doc, "（1）评分卡各特征的可操纵性如何？操纵的成本与分数提升曲线呈现什么形态？", indent=False)
body_para(doc, "（2）操纵后翻转通过审批的客户，其真实违约率相对正常客户高出多少？", indent=False)
body_para(doc, "（3）不同防御机制的有效性与性能代价如何权衡？", indent=False)
heading(doc, "1.3 研究视角与创新点", 2)
body_para(doc,
    "既有信用评分研究多聚焦于提升区分能力（AUC、KS），对输入端的策略性操纵关注不足；而对抗机器"
    "学习的研究主要集中在图像等领域，与信贷业务结合较少。本研究的创新在于：将对抗攻击的攻击者视角"
    "引入评分卡建模，显式刻画借款人的策略性行为；以真实标签不变作为攻击仿真的核心假设，直接测量分数"
    "与真实风险的背离；在统一框架下比较三类防御，给出可落地的成本与效果权衡，而非仅比较模型精度。")

heading(doc, "二、理论基础", 1)
heading(doc, "2.1 评分卡建模流程", 2)
body_para(doc, "标准评分卡包含数据清洗、分箱、WOE编码、IV筛选、逻辑回归、分数映射六个环节。分箱将连续变量离散化，增强模型稳健性并便于处理缺失值与异常值。")
heading(doc, "2.2 WOE与IV", 2)
body_para(doc, "对分箱i，设其中好客户（未违约）数为G_i、坏客户（违约）数为B_i，总体好、坏客户数为G、B，则WOE衡量该箱内好坏分布相对总体的偏离：")
f1 = doc.add_paragraph(); f1.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr1 = f1.add_run("WOE_i = ln[(G_i / G) / (B_i / B)]"); set_run(fr1, size=12, italic=True)
body_para(doc, "特征整体预测力由信息价值IV衡量：")
f2 = doc.add_paragraph(); f2.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr2 = f2.add_run("IV = Σ (G_i/G − B_i/B) · WOE_i"); set_run(fr2, size=12, italic=True)
body_para(doc, "经验上IV小于0.02视为无预测力，0.1至0.3为中等，大于0.5需警惕过拟合或信息泄漏。")
heading(doc, "2.3 分数映射", 2)
body_para(doc, "设逻辑回归输出的坏客户对数几率为ℓ，评分卡按基准分与翻倍分数（PDO）线性映射：")
f3 = doc.add_paragraph(); f3.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr3 = f3.add_run("Factor = PDO / ln2；Offset = S₀ − Factor·lnO₀；Score = Offset − Factor·ℓ")
set_run(fr3, size=12, italic=True)
body_para(doc, "本研究采用行业通用参数S₀=600、基准好坏比O₀=50、PDO=20，即好坏比每翻倍增加20分。")
heading(doc, "2.4 对抗攻击与防御", 2)
body_para(doc,
    "本研究中的攻击属于特征操纵（feature manipulation）：攻击者在推理阶段改变可操纵输入，而非向训练"
    "数据投毒。对应防御包括剔除脆弱特征的稳健建模、基于分布变化的异常检测，以及用操纵样本增强的对抗训练。")

heading(doc, "三、数据与方法", 1)
heading(doc, "3.1 数据集", 2)
body_para(doc,
    "主数据集为Give Me Some Credit（GMSC），包含150000个匿名借款人样本、10个输入特征，目标变量为"
    "未来两年内是否出现90天以上严重逾期，整体违约率6.68%。外部验证采用UCI Default of Credit Card "
    "Clients数据集（30000样本、23个特征、违约率22.1%）。")
heading(doc, "3.2 数据清洗", 2)
body_para(doc,
    "针对GMSC数据的已知问题处理：年龄为0的异常值置缺失；逾期计数中96、98等编码错误截断至20；对"
    "利用率、债务比、收入按99.9%分位winsorize；缺失值按字段性质分别以中位数或0填补。清洗后按75:25"
    "分层划分训练集与测试集。")
heading(doc, "3.3 特征可操纵性分级", 2)
body_para(doc, "结合信贷业务，将特征分为三级：高可操纵（信用利用率、债务比率），可通过突击还款、债务重组短期改变；中可操纵（三类逾期计数、月收入），可通过申诉、时间推移或申报改变；低可操纵（年龄、家属数、信贷账户数、不动产贷款数等人口属性与历史存量）。")
heading(doc, "3.4 攻击形式化", 2)
body_para(doc,
    "对特征向量x，操纵算子T_b以强度b∈[0,1]输出x′=T_b(x;b)，并产生操纵成本。攻击评价的关键在于"
    "真实标签y不随操纵改变。设审批阈值为τ，攻击翻转客户集合为攻击前评分低于阈值、攻击后评分不低于"
    "阈值的客户。研究测量翻转率、翻转客户的真实坏账率以及归一化操纵成本。")

heading(doc, "四、基线评分卡", 1)
heading(doc, "4.1 特征预测力", 2)
body_para(doc,
    "IV筛选结果显示，信用利用率预测力最强（IV=1.07），三类逾期计数次之（0.60至0.89），年龄为中等"
    "预测力（0.24），其余特征较弱。值得注意的是，预测力最强的两个来源——利用率与逾期计数——恰好都"
    "属于高或中可操纵特征，这一结构预示了评分卡的脆弱性。")
add_figure(doc, "01_iv_table.png", "图1  各特征信息价值（橙色为高可操纵特征）")
heading(doc, "4.2 模型表现", 2)
body_para(doc,
    "逻辑回归评分卡在测试集上AUC=0.858、Gini=0.716、KS=0.560，训练集与测试集评分分布的PSI仅"
    "0.0004，远低于0.1的稳定阈值，表明模型泛化良好且无分布偏移。")
add_figure(doc, "02_score_distribution.png", "图2  测试集评分分布（按真实标签）")
heading(doc, "4.3 审批基线", 2)
body_para(doc,
    "以训练集评分中位数（591.2分）为审批线，测试集通过率49.7%，通过客户坏账率1.09%，模型拦截了"
    "91.9%的真实坏客户，构成后续攻击实验的对照基准。")

heading(doc, "五、攻击实验", 1)
heading(doc, "5.1 单特征攻击", 2)
body_para(doc, "四类算子在满强度下的表现差异显著，结果如表1所示。")
make_table(doc,
    ["操纵算子", "平均涨分", "翻转率", "翻转客户真实坏账率"],
    [
        ["利用率", "14.06", "25.79%", "4.91%"],
        ["债务比", "2.77", "4.17%", "2.69%"],
        ["逾期洗白", "7.64", "5.42%", "9.65%"],
        ["收入美化", "1.37", "1.60%", "3.00%"],
    ],
    "表1  单特征满强度攻击结果",
    col_widths=[3.5, 3, 3.5, 4.5])
body_para(doc,
    "利用率操纵因特征权重高、可连续改变而成为最脆弱环节；逾期洗白的翻转率不高，但所获客户的真实"
    "坏账率最高，说明该类操纵筛选出的恰恰是风险最高的人群。")
heading(doc, "5.2 强度扫描", 2)
body_para(doc,
    "随操纵强度由0.1升至1.0，利用率攻击的翻转率单调上升至25.8%，且在强度0.8之后加速；其余三类"
    "攻击的翻转率始终低于6%。成本与涨分关系显示，利用率攻击在低成本区间即可获得可观涨分，边际成本"
    "随强度递增，符合理性借款人先做低成本操纵的行为预期。")
add_figure(doc, "03_attack_flip_curves.png", "图3  各算子操纵强度与翻转率曲线")
heading(doc, "5.3 组合攻击", 2)
body_para(doc,
    "同时施加四类操纵（利用率0.9、债务比0.7、逾期0.6、收入0.3）后，平均涨分24.1，翻转率达46.07%"
    "（17276人），整体通过率从49.7%升至95.6%。翻转客户的真实坏账率为9.92%，是正常通过客户1.09%"
    "的9.1倍，但他们在评分卡上完全具备获批资格——这就是评分失真的直接量化：审批系统无法区分真优质"
    "与包装出来的优质。")
add_figure(doc, "06_bad_rate_gap.png", "图4  正常通过客户与攻击翻转客户的真实坏账率")

heading(doc, "六、防御评估", 1)
heading(doc, "6.1 稳健评分卡", 2)
body_para(doc,
    "剔除两个高可操纵特征（利用率、债务比）后重新训练，测试集翻转率由46.1%骤降至6.6%，而AUC仅"
    "由0.858降至0.826（损失0.031）、KS保持0.52。这表明高可操纵特征虽贡献了短期区分力，但并非不可"
    "替代，剔除它们以极小的精度代价换取了数量级的抗攻击提升，是三类防御中性价比最高的方案。")
heading(doc, "6.2 突变检测", 2)
body_para(doc,
    "基于历史快照与本次申请的差异构建规则：利用率或债务比相对降幅超过50%、逾期计数短期消失、零利用"
    "率与历史逾期并存的矛盾组合，均标记为可疑转人工。对强组合攻击的检测率达100%，干净样本误报率仅"
    "1.0%。其局限同样明确：检测依赖跨期历史数据，对无历史的新客户失效；且仅能拦截大动作操纵，精细"
    "的渐进式操纵可能落在阈值之下。")
heading(doc, "6.3 对抗训练", 2)
body_para(doc,
    "将操纵样本与原始样本混合后重新拟合，测试集AUC保持0.848，翻转率降至36.4%，且翻转客户的真实"
    "坏账率由9.92%降至3.63%。对抗训练不牺牲特征覆盖、实现简单，但对未见过的操纵策略泛化有限，防御"
    "效果弱于稳健卡。")
heading(doc, "6.4 防御方案对比", 2)
make_table(doc,
    ["策略", "翻转率", "AUC", "适用条件"],
    [
        ["基线卡", "46.07%", "0.858", "无操纵环境"],
        ["稳健卡", "6.58%", "0.826", "可接受少量精度损失"],
        ["对抗训练", "36.39%", "0.848", "需保留全特征、操纵模式可预期"],
        ["突变检测", "检测率100%", "不改变模型", "具备跨期历史数据"],
    ],
    "表2  各防御策略对比",
    col_widths=[3, 3, 3, 5.5])
add_figure(doc, "05_defense_comparison.png", "图5  防御前后翻转率与AUC对比")
body_para(doc, "实践中三类防御互补而非互斥：稳健卡作为模型底座，突变检测覆盖审批环节，对抗训练用于已知操纵模式的增强。")

heading(doc, "七、外部验证", 1)
body_para(doc,
    "在UCI台湾信用卡数据上重新构建评分卡（测试集AUC=0.737、KS=0.359），并针对其特征设计利用率、"
    "还款比例、还款状态操纵。结果显示，各强度下翻转客户的真实坏账率介于32.9%至52.9%，而正常通过"
    "客户为11.47%，差距达3至5倍。虽然两个数据集的字段、违约率水平、业务背景均不同，操纵导致高风险"
    "客户混入的结论方向一致，说明该现象具有跨数据集的稳健性，而非GMSC数据上的偶然结果。")
add_figure(doc, "07_external_score_dist.png", "图6  外部验证集评分分布")

heading(doc, "八、讨论与局限", 1)
body_para(doc,
    "第一，操纵仿真的简化：真实操纵受信用额度、可用现金、平台规则等约束，本研究以归一化成本和参数化"
    "强度近似，未刻画个体预算约束下的最优决策，后续可引入成本约束下的优化模型。第二，静态截面数据："
    "GMSC为截面数据，突变检测中的历史快照由攻击前样本代理，真实部署需要面板数据验证。第三，防御的"
    "适应性：攻击者会针对防御调整策略，攻防具有动态博弈性质，单次实验无法覆盖长期均衡。第四，伦理"
    "边界：本研究披露攻击细节的目的是帮助机构理解脆弱性、改进防御，而非提供操纵指南；报告同时提醒，"
    "评分卡设计应在风险控制、金融普惠与公平性之间保持平衡。")

heading(doc, "九、结论", 1)
body_para(doc,
    "本研究从攻击者视角重新审视了信用评分卡的可靠性。主要结论为：第一，评分卡预测力最强的特征恰是"
    "可操纵性较高的特征，结构上存在脆弱性；第二，特征操纵在不改变真实违约风险的情况下可使近半数被拒"
    "客户翻转通过，其真实坏账率可达正常客户的9倍，评分失真可被直接量化；第三，剔除高可操纵特征的"
    "稳健评分卡以极小精度代价获得数量级的抗攻击提升，配合突变检测与对抗训练可形成分层防御；第四，"
    "外部验证证实结论跨数据集稳健。研究表明，信用风控不能只关注模型的区分能力，必须把输入端的策略性"
    "操纵纳入模型设计与评估体系。")

# ---------------- 参考文献 ----------------
doc.add_page_break()
heading(doc, "参考文献", 1)
refs = [
    "[1] Fair Isaac Corporation. FICO Score[EB/OL]. https://www.fico.com/.",
    "[2] Siddiqi N. Credit Risk Scorecards: Developing and Implementing Intelligent Credit Scoring[M]. Hoboken: John Wiley & Sons, 2005.",
    "[3] Kaggle. Give Me Some Credit Dataset[EB/OL]. https://www.kaggle.com/c/GiveMeSomeCredit.",
    "[4] Yeh I C, Lien C H. The comparisons of data mining techniques for the predictive accuracy of probability of default of credit card clients[J]. Expert Systems with Applications, 2009, 36(2): 2473-2480.",
    "[5] UCI Machine Learning Repository. Default of Credit Card Clients[EB/OL]. https://archive.ics.uci.edu/dataset/350/.",
    "[6] UCI Machine Learning Repository. Statlog (German Credit Data)[EB/OL]. https://archive.ics.uci.edu/dataset/144/.",
    "[7] Carrizosa E, et al. A Quadratic Programming Solution to the FICO Credit Scoring Problem[EB/OL]. arXiv:2003.00280, 2020.",
]
for ref in refs:
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    r = p.add_run(ref); set_run(r, size=10.5)

# ---------------- 附录 ----------------
doc.add_page_break()
heading(doc, "附录：数据与复现说明", 1)
body_para(doc,
    "全部数据来自公开匿名数据源，仓库提供一键下载脚本与完整代码，18个单元测试覆盖分箱、WOE、IV、"
    "评分映射、操纵算子与防御规则，实验结果可完整复现。完整代码托管于GitHub："
    "https://github.com/zexuanlei678-dotcom/scorecard-attack-defense。本报告及代码中不包含任何真实姓名、"
    "学号或学校信息。")

doc.save(str(OUT))
print("saved:", OUT)
