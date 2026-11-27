# -*- coding: utf-8 -*-
"""生成上台汇报 PPT 成品（.pptx，16:9）。

设计：纯白底；深蓝=基线/主色、橙红=攻击风险、墨绿=防御；
标题与正文使用微软雅黑，关键数字放大；全程匿名，无emoji；
每页含演讲者备注。运行：python scripts/build_pptx.py
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT = ROOT / "互联网金融汇报PPT.pptx"
REPO = "github.com/zexuanlei678-dotcom/scorecard-attack-defense"

# 配色
NAVY = RGBColor(0x1F, 0x3B, 0x5C)
ORANGE = RGBColor(0xE2, 0x6A, 0x2C)
GREEN = RGBColor(0x2E, 0x7D, 0x52)
INK = RGBColor(0x26, 0x26, 0x26)
GRAY = RGBColor(0x7F, 0x7F, 0x7F)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
L_NAVY = RGBColor(0xEA, 0xF0, 0xF7)
L_ORANGE = RGBColor(0xFB, 0xEA, 0xE0)
L_GREEN = RGBColor(0xE6, 0xF2, 0xEC)
L_GRAY = RGBColor(0xF2, 0xF2, 0xF2)
FONT = "微软雅黑"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
SW, SH = prs.slide_width, prs.slide_height
MARGIN = Inches(0.6)
CONTENT_W = SW - 2 * MARGIN


def new_slide():
    return prs.slides.add_slide(BLANK)


def set_font(run, size=18, bold=False, color=INK, italic=False, font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    rpr = run._r.get_or_add_rPr()
    ea = rpr.find(qn("a:ea"))
    if ea is None:
        ea = rpr.makeelement(qn("a:ea"), {})
        rpr.append(ea)
    ea.set("typeface", font)
    latin = rpr.find(qn("a:latin"))
    if latin is None:
        latin = rpr.makeelement(qn("a:latin"), {})
        rpr.append(latin)
    latin.set("typeface", font)


def textbox(slide, left, top, width, height, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Pt(2); tf.margin_right = Pt(2)
    tf.margin_top = Pt(2); tf.margin_bottom = Pt(2)
    return tf


def para(tf, text, size=18, bold=False, color=INK, align=PP_ALIGN.LEFT,
         italic=False, first=False, space_after=6, line=1.1):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.line_spacing = line
    r = p.add_run(); r.text = text
    set_font(r, size=size, bold=bold, color=color, italic=italic)
    return p


def rect(slide, left, top, width, height, fill, line_color=None, rounded=False, line_w=None):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        left, top, width, height)
    if rounded:
        try:
            shape.adjustments[0] = 0.06
        except Exception:
            pass
    if fill is None:
        shape.fill.background()
    else:
        shape.fill.solid(); shape.fill.fore_color.rgb = fill
    if line_color is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line_color
        shape.line.width = line_w or Pt(1)
    shape.shadow.inherit = False
    return shape


def shape_text(shape, lines, anchor=MSO_ANCHOR.MIDDLE):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Pt(10); tf.margin_right = Pt(10)
    tf.margin_top = Pt(6); tf.margin_bottom = Pt(6)
    for i, (text, size, bold, color, align) in enumerate(lines):
        para(tf, text, size=size, bold=bold, color=color, align=align,
             first=(i == 0), space_after=3, line=1.05)


def header(slide, title, accent=NAVY, kicker=None):
    rect(slide, MARGIN, Inches(0.5), Inches(0.14), Inches(0.62), accent)
    tf = textbox(slide, MARGIN + Inches(0.28), Inches(0.42), CONTENT_W - Inches(0.3), Inches(0.85),
                 anchor=MSO_ANCHOR.MIDDLE)
    para(tf, title, size=28, bold=True, color=NAVY, first=True, space_after=0)
    if kicker:
        kf = textbox(slide, MARGIN + Inches(0.3), Inches(1.18), CONTENT_W, Inches(0.4))
        para(kf, kicker, size=14, color=GRAY, first=True, space_after=0)
    rect(slide, MARGIN, Inches(1.42), CONTENT_W, Pt(1.4), L_GRAY)


def footer(slide):
    tf = textbox(slide, MARGIN, Inches(7.02), CONTENT_W, Inches(0.35))
    para(tf, REPO, size=10, color=GRAY, align=PP_ALIGN.RIGHT, first=True, space_after=0)


def fit_image(slide, name, left, top, max_w, max_h):
    pic = slide.shapes.add_picture(str(RESULTS / name), left, top)
    scale = min(max_w / pic.width, max_h / pic.height)
    pic.width = int(pic.width * scale)
    pic.height = int(pic.height * scale)
    pic.left = int(left + (max_w - pic.width) / 2)
    pic.top = int(top + (max_h - pic.height) / 2)
    return pic


def note(slide, text):
    tf = slide.notes_slide.notes_text_frame
    tf.text = text
    for p in tf.paragraphs:
        for r in p.runs:
            r.font.size = Pt(12); r.font.name = FONT


# ---------------- P1 封面 ----------------
s = new_slide()
rect(s, 0, 0, Inches(0.22), SH, ORANGE)
tf = textbox(s, Inches(0.9), Inches(1.7), Inches(11.6), Inches(2.4))
para(tf, "分数会说谎", size=54, bold=True, color=NAVY, first=True, space_after=10)
para(tf, "信用评分卡的特征操纵攻防研究", size=30, bold=True, color=INK, space_after=12)
para(tf, "When Scores Lie: Feature Manipulation Attacks and Defenses in Credit Scorecards",
     size=15, color=GRAY, italic=True)
rect(s, Inches(0.92), Inches(4.55), Inches(3.2), Pt(2.5), ORANGE)
tf2 = textbox(s, Inches(0.9), Inches(4.8), Inches(11.6), Inches(1.6))
para(tf2, "互联网金融课程期末汇报", size=18, color=INK, first=True, space_after=6)
para(tf2, REPO, size=14, color=GRAY)
note(s, "各位老师同学好，我汇报的题目是《分数会说谎：信用评分卡的特征操纵攻防研究》。"
        "我会用一个反直觉的现象切入：一张看起来很准的评分卡，为什么会被借款人的合法操作骗过。")

# ---------------- P2 开场钩子 ----------------
s = new_slide()
header(s, "一个问题：650分，等于优质客户吗？", ORANGE)
cw = Inches(5.7); ch = Inches(2.7); top = Inches(1.85)
c1 = rect(s, MARGIN, top, cw, ch, L_NAVY, rounded=True)
shape_text(c1, [
    ("客户A", 22, True, NAVY, PP_ALIGN.LEFT),
    ("评分650，获批", 18, False, INK, PP_ALIGN.LEFT),
    ("长期稳定还款的真优质客户", 17, False, GRAY, PP_ALIGN.LEFT)])
c2 = rect(s, SW - MARGIN - cw, top, cw, ch, L_ORANGE, rounded=True)
shape_text(c2, [
    ("客户B", 22, True, ORANGE, PP_ALIGN.LEFT),
    ("评分650，获批", 18, False, INK, PP_ALIGN.LEFT),
    ("申贷前一周突击还款，把分数“养”出来", 17, False, GRAY, PP_ALIGN.LEFT)])
bar = rect(s, MARGIN, Inches(5.05), CONTENT_W, Inches(1.15), NAVY, rounded=True)
shape_text(bar, [
    ("评分卡能区分他们吗？——不能。这就是“评分失真”。", 24, True, WHITE, PP_ALIGN.CENTER)])
footer(s)
note(s, "想象两个人同时申贷，评分都是650、都获批。一个是真优质，另一个是申贷前一周刚把账单还清养出来的。"
        "评分卡看到的输入几乎一样，无法区分。问题不在模型不够准，而在输入会被操纵，这就是我讲的评分失真。")

# ---------------- P3 背景 ----------------
s = new_slide()
header(s, "评分卡：信贷审批的行业标准")
tf = textbox(s, MARGIN, Inches(1.75), Inches(5.6), Inches(3.6))
para(tf, "FICO自1950年代起建立的事实标准", size=19, bold=True, color=NAVY, first=True, space_after=10)
para(tf, "可解释：每个特征对应明确加减分", size=17, space_after=8)
para(tf, "可审计：决策过程可追溯、可复核", size=17, space_after=8)
para(tf, "监管友好：满足模型透明性要求", size=17)
# 流程链
steps = ["分箱", "WOE", "IV筛选", "逻辑回归", "分数映射"]
bx = Inches(6.55); bw = Inches(5.7); n = len(steps); gap = Inches(0.18)
each = (bw - gap * (n - 1)) / n
btop = Inches(2.1)
for i, st in enumerate(steps):
    x = bx + (each + gap) * i
    b = rect(s, x, btop, each, Inches(1.0), L_NAVY, line_color=NAVY, rounded=True)
    shape_text(b, [(st, 15, True, NAVY, PP_ALIGN.CENTER)])
    if i < n - 1:
        af = textbox(s, x + each - Inches(0.02), btop + Inches(0.28), gap + Inches(0.1), Inches(0.5))
        para(af, "→", size=18, bold=True, color=GRAY, align=PP_ALIGN.CENTER, first=True, space_after=0)
bar = rect(s, MARGIN, Inches(4.55), CONTENT_W, Inches(1.1), L_ORANGE, line_color=ORANGE, rounded=True)
shape_text(bar, [
    ("隐含前提：输入特征真实反映借款人的长期信用状况", 21, True, ORANGE, PP_ALIGN.CENTER)])
footer(s)
note(s, "评分卡是FICO从1950年代建立的事实标准，优势是可解释、可审计、监管友好。标准流程是分箱、WOE编码、"
        "IV筛选、逻辑回归再到分数映射。但它有个隐含前提：输入要真实反映长期信用，而这个前提恰恰可能被打破。")

# ---------------- P4 问题提出 ----------------
s = new_slide()
header(s, "被忽视的，是输入端", ORANGE)
tf = textbox(s, MARGIN, Inches(1.75), Inches(6.0), Inches(3.8))
para(tf, "借款人有明确的操纵动机，网上“养征信攻略”普遍存在", size=18, bold=True, color=INK,
     first=True, space_after=14)
qs = [("Q1", "哪些特征可以被操纵？"), ("Q2", "操纵会造成多大的评分失真？"), ("Q3", "如何有效防御？")]
for i, (q, t) in enumerate(qs):
    y = Inches(1.85 + i * 1.15)
    badge = rect(s, Inches(6.9), y, Inches(1.0), Inches(0.9), ORANGE, rounded=True)
    shape_text(badge, [(q, 20, True, WHITE, PP_ALIGN.CENTER)])
    qtf = textbox(s, Inches(8.05), y, Inches(4.7), Inches(0.9), anchor=MSO_ANCHOR.MIDDLE)
    para(qtf, t, size=19, bold=True, color=INK, first=True, space_after=0)
bar = rect(s, MARGIN, Inches(5.5), CONTENT_W, Inches(1.0), L_GREEN, line_color=GREEN, rounded=True)
shape_text(bar, [
    ("创新点：把对抗攻击的“攻击者视角”引入评分卡，而非只追求AUC", 20, True, GREEN, PP_ALIGN.CENTER)])
footer(s)
note(s, "借款人有明确动机，网上养征信攻略也很普遍。我把它拆成三个研究问题：哪些特征可操纵、造成多大失真、"
        "怎么防御。创新点是把对抗攻击的攻击者视角引入评分卡，而不是像传统研究那样只盯着AUC。")

# ---------------- P5 数据与方法 ----------------
s = new_slide()
header(s, "数据与方法")
cw = Inches(5.7); ch = Inches(2.2); top = Inches(1.8)
d1 = rect(s, MARGIN, top, cw, ch, L_NAVY, rounded=True)
shape_text(d1, [
    ("Give Me Some Credit（主数据）", 19, True, NAVY, PP_ALIGN.LEFT),
    ("150000个样本，10个特征", 17, False, INK, PP_ALIGN.LEFT),
    ("违约率6.68%", 17, False, INK, PP_ALIGN.LEFT)])
d2 = rect(s, SW - MARGIN - cw, top, cw, ch, L_GREEN, rounded=True)
shape_text(d2, [
    ("UCI台湾信用卡（外部验证）", 19, True, GREEN, PP_ALIGN.LEFT),
    ("30000个样本，23个特征", 17, False, INK, PP_ALIGN.LEFT),
    ("违约率22.1%", 17, False, INK, PP_ALIGN.LEFT)])
bar = rect(s, MARGIN, Inches(4.5), CONTENT_W, Inches(1.7), L_GRAY, rounded=True)
btf = bar.text_frame; btf.word_wrap = True; btf.vertical_anchor = MSO_ANCHOR.MIDDLE
btf.margin_left = Pt(16)
para(btf, "数据清洗：异常编码截断、99.9%分位winsorize、缺失值填补", size=18, bold=True,
     color=INK, first=True, space_after=6)
para(btf, "按75:25分层划分训练集与测试集，随机种子42", size=17, color=GRAY)
footer(s)
note(s, "主数据是Give Me Some Credit，15万样本、违约率6.68%；外部验证用UCI台湾数据，3万样本。"
        "清洗上处理了编码错误、做了winsorize和缺失填补，再按75比25分层划分，保证可复现。")

# ---------------- P6 可操纵性分级 ----------------
s = new_slide()
header(s, "特征可操纵性分级", ORANGE)
cw = Inches(3.95); ch = Inches(3.35); top = Inches(1.8)
cols = [
    ("高可操纵", ORANGE, L_ORANGE, ["信用利用率", "债务比率"], "突击还款、债务重组即可改变"),
    ("中可操纵", NAVY, L_NAVY, ["三类逾期计数", "月收入"], "申诉、时间推移或申报改变"),
    ("低可操纵", GREEN, L_GREEN, ["年龄、家属数", "账户数、不动产贷款"], "人口属性与历史存量，难短期改变"),
]
for i, (name, c, lc, feats, desc) in enumerate(cols):
    x = MARGIN + (cw + Inches(0.22)) * i
    head = rect(s, x, top, cw, Inches(0.75), c, rounded=True)
    shape_text(head, [(name, 19, True, WHITE, PP_ALIGN.CENTER)])
    body = rect(s, x, top + Inches(0.85), cw, ch - Inches(0.85), lc, rounded=True)
    btf = body.text_frame; btf.word_wrap = True; btf.vertical_anchor = MSO_ANCHOR.MIDDLE
    btf.margin_left = Pt(12); btf.margin_right = Pt(12)
    for j, f in enumerate(feats):
        para(btf, f, size=18, bold=True, color=INK, first=(j == 0), space_after=8)
    para(btf, desc, size=14, color=GRAY, space_after=0)
bar = rect(s, MARGIN, Inches(5.55), CONTENT_W, Inches(0.95), ORANGE, rounded=True)
shape_text(bar, [("预测力最强的特征，恰恰是高/中可操纵特征", 20, True, WHITE, PP_ALIGN.CENTER)])
footer(s)
note(s, "我把特征分成三级：利用率和债务比是高可操纵，逾期计数和收入是中可操纵，人口属性和历史存量是低可操纵。"
        "关键埋点在这：后面会看到，预测力最强的恰恰是高、中可操纵特征，这就埋下了脆弱性。")

# ---------------- P7 基线表现 ----------------
s = new_slide()
header(s, "基线评分卡：一张“好卡”")
fit_image(s, "02_score_distribution.png", MARGIN, Inches(1.7), Inches(7.2), Inches(4.6))
panel = rect(s, Inches(8.0), Inches(1.75), Inches(4.75), Inches(4.5), L_NAVY, rounded=True)
ptf = panel.text_frame; ptf.word_wrap = True; ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
ptf.margin_left = Pt(16)
metrics = [("AUC", "0.858"), ("KS", "0.560"), ("PSI", "0.0004"),
           ("通过客户坏账率", "1.09%"), ("坏客户拦截率", "91.9%")]
for i, (k, v) in enumerate(metrics):
    para(ptf, k, size=14, color=GRAY, first=(i == 0), space_after=0)
    para(ptf, v, size=26, bold=True, color=NAVY, space_after=10)
footer(s)
note(s, "这是基线评分卡，测试集AUC0.858、KS0.56，PSI只有0.0004，非常稳定。通过客户坏账率1.09%，"
        "拦截了91.9%的坏客户。按传统标准，这确实是一张好卡，接下来看它怎么被攻破。")

# ---------------- P8 攻击设计 ----------------
s = new_slide()
header(s, "攻击设计：特征变，真实标签不变", ORANGE)
bar = rect(s, MARGIN, Inches(1.75), CONTENT_W, Inches(1.15), L_ORANGE, line_color=ORANGE, rounded=True)
shape_text(bar, [
    ("核心假设：操纵算子T_b把特征x变成x′，但真实违约标签y不变", 21, True, ORANGE, PP_ALIGN.CENTER)])
ops = [("利用率", "降低额度利用率"), ("债务比", "重组压低负债比"),
       ("逾期洗白", "清除逾期记录"), ("收入美化", "申报更高收入")]
cw = Inches(2.95); ch = Inches(1.7); top = Inches(3.3); gap = Inches(0.18)
for i, (k, d) in enumerate(ops):
    x = MARGIN + (cw + gap) * i
    b = rect(s, x, top, cw, ch, L_GRAY, line_color=ORANGE, rounded=True)
    btf = b.text_frame; btf.word_wrap = True; btf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(btf, k, size=18, bold=True, color=ORANGE, align=PP_ALIGN.CENTER, first=True, space_after=6)
    para(btf, d, size=14, color=INK, align=PP_ALIGN.CENTER, space_after=0)
bar2 = rect(s, MARGIN, Inches(5.4), CONTENT_W, Inches(0.95), NAVY, rounded=True)
shape_text(bar2, [("翻转客户：攻击前被拒、攻击后评分越过审批线的客户", 19, True, WHITE, PP_ALIGN.CENTER)])
footer(s)
note(s, "攻击设计的核心假设很重要：操纵只改变特征，真实违约标签不变。我设计了四类算子，各自带操纵成本。"
        "重点观察翻转客户，也就是攻击前被拒、攻击后越过审批线的人，再去看他们的真实坏账率。")

# ---------------- P9 单特征攻击 ----------------
s = new_slide()
header(s, "单特征攻击：利用率最脆弱", ORANGE)
fit_image(s, "03_attack_flip_curves.png", MARGIN, Inches(1.7), Inches(7.4), Inches(4.6))
panel = rect(s, Inches(8.15), Inches(1.75), Inches(4.6), Inches(4.5), L_ORANGE, rounded=True)
ptf = panel.text_frame; ptf.word_wrap = True; ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
ptf.margin_left = Pt(14); ptf.margin_right = Pt(14)
para(ptf, "利用率操纵", size=15, color=GRAY, first=True, space_after=0)
para(ptf, "满强度翻转25.8%", size=22, bold=True, color=ORANGE, space_after=12)
para(ptf, "逾期洗白", size=15, color=GRAY, space_after=0)
para(ptf, "客户坏账率最高9.65%", size=22, bold=True, color=ORANGE, space_after=12)
para(ptf, "低成本区间即可获得可观涨分", size=16, bold=True, color=INK, space_after=0)
footer(s)
note(s, "单特征攻击里，利用率操纵最脆弱，满强度翻转率25.8%。逾期洗白翻转率不高，但得手客户坏账率最高，"
        "达9.65%。成本曲线还显示，低成本就能换来可观涨分，理性借款人完全有动力这么做。")

# ---------------- P10 组合攻击 ----------------
s = new_slide()
header(s, "组合攻击：近半数被拒客户“洗白”", ORANGE)
# 顶部三个数字
nums = [("平均涨分", "24.1"), ("翻转率", "46.1%"), ("通过率", "49.7%→95.6%")]
cw = Inches(3.95); top = Inches(1.7)
for i, (k, v) in enumerate(nums):
    x = MARGIN + (cw + Inches(0.22)) * i
    b = rect(s, x, top, cw, Inches(1.2), L_NAVY, rounded=True)
    btf = b.text_frame; btf.vertical_anchor = MSO_ANCHOR.MIDDLE
    para(btf, k, size=14, color=GRAY, align=PP_ALIGN.CENTER, first=True, space_after=2)
    para(btf, v, size=26, bold=True, color=NAVY, align=PP_ALIGN.CENTER, space_after=0)
fit_image(s, "06_bad_rate_gap.png", MARGIN, Inches(3.15), Inches(7.3), Inches(3.4))
panel = rect(s, Inches(8.1), Inches(3.15), Inches(4.65), Inches(3.4), ORANGE, rounded=True)
ptf = panel.text_frame; ptf.word_wrap = True; ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
ptf.margin_left = Pt(14)
para(ptf, "翻转客户真实坏账率", size=15, color=WHITE, first=True, space_after=2)
para(ptf, "9.92%", size=34, bold=True, color=WHITE, space_after=8)
para(ptf, "正常客户1.09%", size=16, color=WHITE, space_after=2)
para(ptf, "相差9.1倍", size=26, bold=True, color=WHITE, space_after=0)
footer(s)
note(s, "这是核心证据页。四类操纵同时施加，平均涨24分，46.1%的被拒客户翻转，通过率从49.7%飙到95.6%。"
        "而这些翻转客户的真实坏账率是9.92%，正常客户只有1.09%，相差9.1倍。评分虚高，真实风险却一点没降。")

# ---------------- P11 三种防御 ----------------
s = new_slide()
header(s, "三种防御", GREEN)
defs = [
    ("稳健评分卡", GREEN, L_GREEN, ["剔除高可操纵特征", "翻转率46.1%→6.6%", "AUC仅损失0.031"]),
    ("突变检测", NAVY, L_NAVY, ["历史快照对比", "强攻击检测率100%", "误报1%，新客户失效"]),
    ("对抗训练", ORANGE, L_ORANGE, ["操纵样本增强", "翻转率→36.4%", "得手坏账率→3.63%"]),
]
cw = Inches(3.95); ch = Inches(3.7); top = Inches(1.8)
for i, (name, c, lc, items) in enumerate(defs):
    x = MARGIN + (cw + Inches(0.22)) * i
    head = rect(s, x, top, cw, Inches(0.75), c, rounded=True)
    shape_text(head, [(name, 19, True, WHITE, PP_ALIGN.CENTER)])
    body = rect(s, x, top + Inches(0.85), cw, ch - Inches(0.85), lc, rounded=True)
    btf = body.text_frame; btf.word_wrap = True; btf.vertical_anchor = MSO_ANCHOR.MIDDLE
    btf.margin_left = Pt(14)
    for j, it in enumerate(items):
        para(btf, it, size=17, bold=(j > 0), color=INK if j == 0 else c,
             first=(j == 0), space_after=10)
footer(s)
note(s, "我评估了三类防御。稳健卡剔除高可操纵特征，翻转率降到6.6%，AUC只损失0.031。突变检测靠历史快照，"
        "强攻击检测率100%但对新客户失效。对抗训练翻转率降到36.4%，得手客户坏账率降到3.63%。")

# ---------------- P12 防御对比与落地 ----------------
s = new_slide()
header(s, "分层防御：组合使用", GREEN)
fit_image(s, "05_defense_comparison.png", MARGIN, Inches(1.7), Inches(7.4), Inches(4.5))
panel = rect(s, Inches(8.15), Inches(1.75), Inches(4.6), Inches(4.5), L_GREEN, rounded=True)
ptf = panel.text_frame; ptf.word_wrap = True; ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
ptf.margin_left = Pt(14)
para(ptf, "落地建议", size=18, bold=True, color=GREEN, first=True, space_after=10)
para(ptf, "稳健卡做模型底座", size=17, color=INK, space_after=8)
para(ptf, "突变检测覆盖审批环节", size=17, color=INK, space_after=8)
para(ptf, "对抗训练增强已知模式", size=17, color=INK, space_after=12)
para(ptf, "性价比：稳健卡 > 对抗训练 > 突变检测", size=15, bold=True, color=GREEN, space_after=0)
footer(s)
note(s, "这三类防御不是互斥的，应该组合使用：稳健卡做底座，突变检测覆盖审批，对抗训练增强已知模式。"
        "性价比上稳健卡最高。它们形成一道分层防线，而不是靠单一手段解决所有问题。")

# ---------------- P13 外部验证与局限 ----------------
s = new_slide()
header(s, "外部验证：结论跨数据集稳健")
fit_image(s, "07_external_score_dist.png", MARGIN, Inches(1.75), Inches(7.2), Inches(4.4))
panel = rect(s, Inches(8.0), Inches(1.75), Inches(4.75), Inches(2.2), L_GREEN, rounded=True)
ptf = panel.text_frame; ptf.word_wrap = True; ptf.vertical_anchor = MSO_ANCHOR.MIDDLE
ptf.margin_left = Pt(14)
para(ptf, "台湾数据翻转客户坏账率", size=14, color=GRAY, first=True, space_after=2)
para(ptf, "32.9%~52.9%", size=24, bold=True, color=GREEN, space_after=6)
para(ptf, "正常客户11.5%，方向一致", size=15, color=INK, space_after=0)
lim = rect(s, Inches(8.0), Inches(4.15), Inches(4.75), Inches(2.1), L_GRAY, rounded=True)
ltf = lim.text_frame; ltf.word_wrap = True; ltf.vertical_anchor = MSO_ANCHOR.MIDDLE
ltf.margin_left = Pt(14)
para(ltf, "局限", size=15, bold=True, color=NAVY, first=True, space_after=4)
para(ltf, "操纵成本为归一化近似", size=14, color=INK, space_after=3)
para(ltf, "静态截面数据，非面板", size=14, color=INK, space_after=3)
para(ltf, "攻防存在动态博弈", size=14, color=INK, space_after=0)
footer(s)
note(s, "在台湾数据上，翻转客户坏账率32.9%到52.9%，正常客户11.5%，差距方向一致，说明结论跨数据集稳健。"
        "我也诚实交代局限：操纵成本是归一化近似、用的是静态截面、而且攻防是动态博弈，这些都需要后续研究。")

# ---------------- P14 结论金句 ----------------
s = new_slide()
tf = textbox(s, MARGIN, Inches(0.7), CONTENT_W, Inches(2.2))
para(tf, "结论", size=30, bold=True, color=NAVY, first=True, space_after=10)
para(tf, "1. 强预测力特征往往可操纵，评分卡结构上存在脆弱性", size=18, color=INK, space_after=8)
para(tf, "2. 操纵可量化地制造约9倍的真实坏账", size=18, color=INK, space_after=8)
para(tf, "3. 剔除脆弱特征的稳健卡可低成本落地防御", size=18, color=INK)
bar = rect(s, MARGIN, Inches(3.55), CONTENT_W, Inches(2.0), NAVY, rounded=True)
btf = bar.text_frame; btf.word_wrap = True; btf.vertical_anchor = MSO_ANCHOR.MIDDLE
btf.margin_left = Pt(24); btf.margin_right = Pt(24)
para(btf, "模型的准确率，回答不了输入是否诚实。", size=26, bold=True, color=WHITE,
     align=PP_ALIGN.CENTER, first=True, space_after=8)
para(btf, "风控的第一步，是承认数据会说谎。", size=26, bold=True, color=WHITE,
     align=PP_ALIGN.CENTER, space_after=0)
tf2 = textbox(s, MARGIN, Inches(6.0), CONTENT_W, Inches(0.8))
para(tf2, REPO, size=14, color=GRAY, align=PP_ALIGN.CENTER, first=True, space_after=0)
para(tf2, "感谢聆听，欢迎提问", size=16, bold=True, color=ORANGE, align=PP_ALIGN.CENTER)
note(s, "总结三点：强预测力特征往往可操纵；操纵能制造约9倍真实坏账；稳健卡可以低成本防御。"
        "最后用一句话收尾：模型的准确率回答不了输入是否诚实，风控的第一步是承认数据会说谎。谢谢大家。")

prs.save(str(OUT))
print("saved:", OUT, "slides:", len(prs.slides._sldIdLst))
