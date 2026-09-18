"""'검색 LLM이면 되지 않나?' 방어용 슬라이드 2장 — 팀 발표 초안(발표 초안.pptx)과 같은 스타일.
  A. 지식그래프라서 답할 수 있는 질문 — 집계 차트 2개 + 수치 타일 3개 (전부 PowerPoint 네이티브 차트·도형)
  B. 웹 검색 LLM vs 우리 — 비교표
숫자 출처: data/graph.json (LLM 0회), docs/20260916_발표_수치_4-5장.md, 발표 초안 7장 챗봇 캡처.
사용: kg_slides.py out.pptx
"""
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree

# 팀 초안과 같은 값 (2장에서 읽음): 배경 F5F7FC, 번호 E8574A 20pt, 제목 1E2761 26pt, 부제 5A6072 13pt, Calibri
BG, NUM, TITLE, MUTED, TEXT = "F5F7FC", "E8574A", "1E2761", "5A6072", "1F2430"
CARD, LINE = "FFFFFF", "D9DCE3"
NAVY_MARK, CORAL_MARK, GREEN_MARK = "3A4FA8", "E8574A", "2F9E63"   # 막대·강조색 — validate_palette.js 통과 (L 밴드·대비 PASS)
TRACK = "DCE1F3"                                                    # 미터 트랙: 남색 램프의 밝은 단
GRAY = "9AA3B2"
FONT = "Calibri"
FOOTER = "LG CNS AI캠퍼스 · Knowledge Graph 과정 project - LG 직무 추천 AI Agent"

prs = Presentation(); prs.slide_width = Inches(13.333); prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def rgb(h): return RGBColor.from_string(h)


def rect(s, x, y, w, h, fill, shape=MSO_SHAPE.RECTANGLE, radius=None, line=None):
    o = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    o.fill.solid(); o.fill.fore_color.rgb = rgb(fill)
    if line: o.line.color.rgb = rgb(line); o.line.width = Pt(0.75)
    else: o.line.fill.background()
    o.shadow.inherit = False
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE: o.adjustments[0] = radius
    return o


def tb(s, x, y, w, h, text, size=12, bold=False, color=TEXT, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, wrap=True):
    """text: str 또는 [[(run, {size,bold,color}), ...] 문단들]"""
    t = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = t.text_frame; tf.word_wrap = wrap; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paras = text if isinstance(text, list) else [[(text, {})]]
    for i, runs in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); p.alignment = align
        for rt, o in runs:
            r = p.add_run(); r.text = rt; f = r.font; f.name = FONT
            f.size = Pt(o.get("size", size)); f.bold = o.get("bold", bold); f.color.rgb = rgb(o.get("color", color))
    return t


def header(s, num, title, sub):
    s.background.fill.solid(); s.background.fill.fore_color.rgb = rgb(BG)
    tb(s, 0.5, 0.42, 1.0, 0.5, num, 20, True, NUM)
    tb(s, 0.5, 0.78, 11.0, 0.55, title, 26, True, TITLE)
    tb(s, 0.5, 1.32, 11.3, 0.4, sub, 13, False, MUTED)
    tb(s, 0.5, 7.08, 9.5, 0.3, FOOTER, 9, False, MUTED)
    motif(s)


def motif(s, x0=11.95, y0=0.58, d=0.12, gap=0.4):
    """우상단 스키마 모티프 — 전공 → 역량 ← 직무, 아래 하위 역량 ↑ (motif_patch.py 와 동일)"""
    xm, xs, xj = x0, x0 + gap, x0 + 2 * gap; ys = y0 + gap * 0.8; r = d / 2 + 0.02
    for (a, b, c, d2), col in (((xm + r, y0, xs - r, y0), TITLE), ((xj - r, y0, xs + r, y0), GREEN_MARK), ((xs, ys - r, xs, y0 + r), GRAY)):
        cn = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(a), Inches(b), Inches(c), Inches(d2))
        cn.line.color.rgb = rgb(col); cn.line.width = Pt(1)
        ln = cn.line._get_or_add_ln(); t = etree.SubElement(ln, qn("a:tailEnd")); t.set("type", "triangle"); t.set("w", "sm"); t.set("len", "sm")
    for cx, cy, dd, col in ((xm, y0, d, TITLE), (xs, y0, d, CORAL_MARK), (xj, y0, d, GREEN_MARK), (xs, ys, d * 0.7, GRAY)):
        rect(s, cx - dd / 2, cy - dd / 2, dd, dd, col, MSO_SHAPE.OVAL)


def card(s, x, y, w, h, title, sub=None):
    rect(s, x, y, w, h, CARD, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.04, line=LINE)
    tb(s, x + 0.25, y + 0.18, w - 0.5, 0.3, title, 13, True, TITLE)
    if sub: tb(s, x + 0.25, y + 0.48, w - 0.5, 0.28, sub, 10, False, MUTED)


def bar_chart(s, x, y, w, h, cats, vals, color, vmax):
    """가로 막대 1계열: 값은 막대 끝에, 축·격자·범례 없음 (값을 전부 표시하므로 축 생략)."""
    cd = CategoryChartData(); cd.categories = cats; cd.add_series("건수", vals)
    gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart; ch.has_legend = False; ch.has_title = False
    ch.font.name = FONT; ch.font.size = Pt(11); ch.font.color.rgb = rgb(TEXT)
    pl = ch.plots[0]; pl.gap_width = 80; pl.vary_by_categories = False
    pl.has_data_labels = True; dl = pl.data_labels
    dl.position = XL_LABEL_POSITION.OUTSIDE_END; dl.number_format = "0"; dl.number_format_is_linked = False
    dl.font.size = Pt(11); dl.font.bold = True; dl.font.color.rgb = rgb(TEXT)
    ser = pl.series[0]; ser.format.fill.solid(); ser.format.fill.fore_color.rgb = rgb(color); ser.format.line.fill.background()
    ca = ch.category_axis; ca.reverse_order = True; ca.has_major_gridlines = False
    ca.tick_labels.font.size = Pt(11); ca.tick_labels.font.color.rgb = rgb(TEXT); ca.format.line.color.rgb = rgb(LINE)
    va = ch.value_axis; va.visible = False; va.has_major_gridlines = False; va.minimum_scale = 0; va.maximum_scale = vmax
    return gf


def table(s, x, y, rows, col_w, row_h, font_size=11):
    shp = s.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(sum(col_w)), Inches(row_h * len(rows)))
    tbl = shp.table; tblPr = tbl._tbl.tblPr; tblPr.set("bandRow", "0"); tblPr.set("firstRow", "0")
    st = tblPr.find(qn("a:tableStyleId"))
    if st is not None: tblPr.remove(st)
    for ci, cw in enumerate(col_w): tbl.columns[ci].width = Inches(cw)
    for ri, row in enumerate(rows):
        tbl.rows[ri].height = Inches(row_h)
        for ci, val in enumerate(row):
            c = tbl.cell(ri, ci); c.margin_left = c.margin_right = Inches(0.12); c.margin_top = c.margin_bottom = Inches(0.05)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE; c.fill.solid()
            c.fill.fore_color.rgb = rgb(TITLE if ri == 0 else ("EEF1FB" if ci == 2 else CARD))
            tcPr = c._tc.get_or_add_tcPr()
            for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
                ln = etree.SubElement(tcPr, qn(tag)); ln.set("w", "6350"); ln.set("cap", "flat"); ln.set("cmpd", "sng")
                sf = etree.SubElement(ln, qn("a:solidFill")); cc = etree.SubElement(sf, qn("a:srgbClr")); cc.set("val", "FFFFFF" if ri == 0 else LINE)
            tf = c.text_frame; tf.word_wrap = True
            runs = val if isinstance(val, list) else [(str(val), {})]
            p = tf.paragraphs[0]
            for rt, o in runs:
                r = p.add_run(); r.text = rt; f = r.font; f.name = FONT; f.size = Pt(o.get("size", font_size))
                f.bold = o.get("bold", ri == 0 or ci == 0); f.color.rgb = rgb(o.get("color", "FFFFFF" if ri == 0 else TEXT))
    return shp


# ── 데이터 (data/graph.json 집계, 2026-09-18) ──────────────────────────────
SKILL_TOP = [("기계공학", 16), ("전기공학", 15), ("데이터 분석", 13), ("Python", 11), ("머신러닝", 10)]
MAJOR_TOP = [("전기·정보공학부", 48), ("기계공학부", 32), ("컴퓨터공학부", 31), ("스마트시스템과학과", 31), ("재료공학부", 30)]
LINKED, TOTAL_MAJORS = 58, 61
TOK_ALL, TOK_KG = 115_000, 1_400
CHAT_TOTAL, CHAT_REAL = 9, 2

# ── A. 집계 ───────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, "07", "지식그래프라서 답할 수 있는 질문", "어느 웹페이지에도 없는 답 — 두 출처를 이어 둔 그래프를 세어서 즉시 (LLM 0회)")
cw, cy, chh = 6.05, 1.85, 3.55
card(s, 0.5, cy, cw, chh, "신입 직무 75개가 가장 많이 요구하는 역량", "요구 역량(REQUIRES) 기준 · 직무 수")
bar_chart(s, 0.6, cy + 0.8, cw - 0.3, chh - 0.9, [c for c, _ in SKILL_TOP], [v for _, v in SKILL_TOP], CORAL_MARK, 20)
card(s, 6.78, cy, cw, chh, "LG 신입 직무와 가장 많이 이어지는 전공", "전공이 기르는 역량이 요구 역량과 겹치는 신입 직무 수 (IS_A 포함)")
bar_chart(s, 6.88, cy + 0.8, cw - 0.3, chh - 0.9, [c for c, _ in MAJOR_TOP], [v for _, v in MAJOR_TOP], NAVY_MARK, 60)

# 수치 타일 3개
ty, th, tw, tg = 5.6, 1.3, 4.0, 0.165
# ① 58 / 61 — 미터
x = 0.5; card(s, x, ty, tw, th, "LG 신입 직무와 이어지는 전공")
tb(s, x + 0.25, ty + 0.5, 2.2, 0.5, [[("58", {"size": 28, "bold": True, "color": TITLE}), (" / 61 전공", {"size": 13, "color": MUTED})]], anchor=MSO_ANCHOR.BOTTOM)
rect(s, x + 0.25, ty + 1.02, tw - 0.5, 0.1, TRACK, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
rect(s, x + 0.25, ty + 1.02, (tw - 0.5) * LINKED / TOTAL_MAJORS, 0.1, NAVY_MARK, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
tb(s, x + 1.9, ty + 0.66, tw - 2.15, 0.3, "안 이어지는 전공 3개", 10, False, MUTED, align=PP_ALIGN.RIGHT)
# ② 토큰 115k vs 1.4k — 막대 2개
x = 0.5 + tw + tg; card(s, x, ty, tw, th, "질문 1건에 LLM이 읽는 양 (토큰)")
bw = tw - 0.5 - 1.8
for i, (lab, v, col) in enumerate((("자료를 매번 넣기", TOK_ALL, GRAY), ("그래프 읽기", TOK_KG, NAVY_MARK))):
    yy = ty + 0.56 + i * 0.34
    tb(s, x + 0.25, yy, 1.35, 0.26, lab, 10, False, MUTED, anchor=MSO_ANCHOR.MIDDLE)
    rect(s, x + 1.65, yy + 0.05, max(bw * v / TOK_ALL, 0.04), 0.16, col, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.3)
    tb(s, x + 1.65 + max(bw * v / TOK_ALL, 0.04) + 0.08, yy, 1.0, 0.26, f"{v/1000:g}k", 11, True, TEXT, anchor=MSO_ANCHOR.MIDDLE)
# ③ 챗봇 과목 9개 중 실재 2개 — 와플
x = 0.5 + 2 * (tw + tg); card(s, x, ty, tw, th, "챗봇이 든 '통계학과 과목' 9개 중 실재")
tb(s, x + 0.25, ty + 0.5, 1.4, 0.5, [[("2", {"size": 28, "bold": True, "color": TITLE}), (" / 9", {"size": 13, "color": MUTED})]], anchor=MSO_ANCHOR.BOTTOM)
for i in range(CHAT_TOTAL):
    sq = 0.22; sx = x + 1.5 + i * (sq + 0.06)
    rect(s, sx, ty + 0.66, sq, sq, CORAL_MARK if i < CHAT_REAL else CARD, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15, line=None if i < CHAT_REAL else GRAY)
tb(s, x + 0.25, ty + 0.98, tw - 0.5, 0.26, "우리 카드의 과목·직무명은 전부 실재 (자동 확인)", 9.5, False, MUTED)
s.notes_slide.notes_text_frame.text = ("'웹 검색 LLM이면 되지 않나?'에 대한 답. 왼쪽 두 차트는 검색으로는 못 만드는 집계 — 교육과정과 채용공고를 같은 어휘로 이어 둔 그래프에서 "
                                       "LLM 없이 즉시 센 것. 아래: 61개 전공 중 58개가 LG 신입 직무와 이어짐 / 그래프 없이 자료를 매번 LLM에 넣으면 요청당 약 115k 토큰, 그래프를 읽으면 약 1.4k / "
                                       "챗봇이 통계학과 과목이라고 든 9개 중 교육과정에 실제 있는 건 수리통계 1·2, 회귀분석 및 실습 2개뿐.")

# ── B. 비교표 ─────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, "07", "\"웹 검색 되는 LLM이면 되지 않나?\"", "검색은 문서를 찾아 주고, 우리는 문서 두 뭉치를 미리 이어 둔 것 — 좁은 질문을 근거 있게")
rows = [["", "웹 검색 LLM", "지식그래프 (우리)"],
        ["비교 범위", "떠오르는 전공 몇 개", "전공 61개 · 신입 직무 75개 전수 비교 → 순위 · %"],
        ["두 출처 잇기", "페이지 단위로 읽음 — 교육과정과 채용공고를 같은 말로 잇지 못함", "사전 139개 + 상하 계층 102개로 미리 이어 둠 (공통 역량 8 → 30, 직무 연결 0 → 75)"],
        ["근거", "과목명을 지어냄 — 통계학과 과목 9개 중 실재 2개", "카드의 모든 과목·직무 이름이 데이터에 있음 + 출처(대학알리미 · LG Careers)"],
        ["재현성", "실행마다 답이 다름", "같은 역량 태그 → 항상 같은 답 (판정은 계산) · 평가셋 24/24"],
        ["거꾸로 묻기", "직무 → 전공은 새로 검색, 매번 다름", "같은 그래프를 반대로 읽음 (--job)"],
        ["질문 1건 비용", "자료를 다 넣으면 ≈115k 토큰", "≈1.4k 토큰 · LLM은 태그 1회 + 설명 1회"],
        ["범위 (솔직히)", [("전국 대학 · 전 기업 — 넓은 질문은 이쪽이 낫다", {"bold": False})], [("서울대 1개교 · LG 신입 공고 스냅샷 — 좁지만 검증 가능", {"bold": False})]]]
table(s, 0.5, 1.85, rows, [1.7, 4.6, 6.03], 0.6, font_size=11)
rect(s, 0.5, 6.75, 12.33, 0.05, LINE)
tb(s, 0.5, 6.82, 12.3, 0.25, "숫자 출처: data/graph.json 집계 · docs/20260916_발표_수치_4-5장.md(토큰 실측) · 7장 챗봇 캡처 대조", 9, False, MUTED)
s.notes_slide.notes_text_frame.text = "마지막 줄을 먼저 인정하고 넘어갈 것: 넓게 묻는 건 검색 LLM이 낫고, 좁은 질문을 근거 있게 답하는 게 우리 몫."

out = sys.argv[1] if len(sys.argv) > 1 else "kg_slides.pptx"
prs.save(out); print("saved", out, len(prs.slides), "slides")
