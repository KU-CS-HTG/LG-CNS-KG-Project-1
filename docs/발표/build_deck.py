# -*- coding: utf-8 -*-
"""발표 PPT 초안 생성기 — python-pptx. 테마 'Graph Ink' (흰 바탕 · 남색 · 코랄 강조 · 노드-엣지 모티프)."""
import sys
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.oxml.ns import qn
from lxml import etree

THEME = sys.argv[1] if len(sys.argv) > 1 else "A"
THEMES = {
    "A": dict(name="Graph Ink", bg="FFFFFF", text="1F2430", muted="6B7280", primary="2F3C7E", accent="F96167",
              good="1A9E7A", card="F3F4F8", card2="EEF1FB", dark="1B2140", dark_text="FFFFFF", dark_muted="B8C0E0", mono="Consolas"),
    "B": dict(name="Dark Board", bg="0F172A", text="E5E7EB", muted="94A3B8", primary="5EEAD4", accent="FB7185",
              good="34D399", card="1E293B", card2="172033", dark="0B1020", dark_text="F8FAFC", dark_muted="94A3B8", mono="Consolas"),
    "C": dict(name="Signal Red", bg="FFFFFF", text="1A1A1A", muted="6B6B6B", primary="A50034", accent="A50034",
              good="2E7D32", card="F5F5F5", card2="FBECEF", dark="2B0A14", dark_text="FFFFFF", dark_muted="D9B8C2", mono="Consolas"),
}
T = THEMES[THEME]
FONT = "Malgun Gothic"
W, H = 13.333, 7.5

prs = Presentation()
prs.slide_width = Inches(W); prs.slide_height = Inches(H)
BLANK = prs.slide_layouts[6]


def rgb(h): return RGBColor.from_string(h)


def rect(slide, x, y, w, h, fill, shape=MSO_SHAPE.RECTANGLE, line=None, radius=None, shadow=False):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = rgb(fill)
    if line: s.line.color.rgb = rgb(line); s.line.width = Pt(0.75)
    else: s.line.fill.background()
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    if not shadow:
        # 그림자 제거
        spPr = s._element.spPr
        el = etree.SubElement(spPr, qn("a:effectLst"))
    s.text_frame.text = ""
    return s


def tb(slide, x, y, w, h, text, size=14, bold=False, color=None, align=PP_ALIGN.LEFT, font=FONT, anchor=MSO_ANCHOR.TOP,
       line_spacing=1.15, italic=False):
    """텍스트 상자. text 는 str 또는 [(text, {opts}), ...] 런 목록 또는 문단 목록(list of list)."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = text if isinstance(text, list) and text and isinstance(text[0], list) else [text]
    for pi, para in enumerate(paras):
        p = tf.paragraphs[0] if pi == 0 else tf.add_paragraph()
        p.alignment = align; p.line_spacing = line_spacing
        runs = para if isinstance(para, list) else [(para, {})]
        for rtext, opts in (runs if isinstance(runs[0], tuple) else [(runs, {})]):
            r = p.add_run(); r.text = rtext
            f = r.font; f.name = opts.get("font", font); f.size = Pt(opts.get("size", size)); f.bold = opts.get("bold", bold)
            f.italic = opts.get("italic", italic)
            f.color.rgb = rgb(opts.get("color", color or T["text"]))
    return box


def bullets(slide, x, y, w, h, items, size=14, color=None, gap=6, bullet_color=None, font=FONT):
    """글머리 기호 문단들. items: str 또는 (str, level) 또는 [(run, opts), ...]."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, it in enumerate(items):
        level = 0
        if isinstance(it, tuple) and len(it) == 2 and isinstance(it[1], int):
            it, level = it
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.12; p.space_after = Pt(gap)
        pPr = p._p.get_or_add_pPr()
        indent = 0.22 + 0.25 * level
        pPr.set("marL", str(int(Inches(indent)))); pPr.set("indent", str(-int(Inches(0.22))))
        bu = etree.SubElement(pPr, qn("a:buClr")); srgb = etree.SubElement(bu, qn("a:srgbClr")); srgb.set("val", bullet_color or T["primary"])
        buf = etree.SubElement(pPr, qn("a:buFont")); buf.set("typeface", "Arial")
        bc = etree.SubElement(pPr, qn("a:buChar")); bc.set("char", "•" if level == 0 else "–")
        runs = it if isinstance(it, list) else [(it, {})]
        for rtext, opts in runs:
            r = p.add_run(); r.text = rtext
            f = r.font; f.name = opts.get("font", font); f.size = Pt(opts.get("size", size - (1 if level else 0)))
            f.bold = opts.get("bold", False); f.color.rgb = rgb(opts.get("color", color or T["text"]))
    return box


def node_motif(slide, x, y, scale=1.0, colors=None):
    """노드-엣지 모티프: 원 3개 + 선 2개."""
    colors = colors or [T["primary"], T["accent"], T["primary"]]
    pts = [(0, 0.25), (0.55, 0), (1.05, 0.3)]
    r = 0.22 * scale
    # 선 먼저
    for (ax, ay), (bx, by) in [(pts[0], pts[1]), (pts[1], pts[2])]:
        c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x + ax * scale + r / 2), Inches(y + ay * scale + r / 2),
                                       Inches(x + bx * scale + r / 2), Inches(y + by * scale + r / 2))
        c.line.color.rgb = rgb(T["muted"]); c.line.width = Pt(1.5 * scale)
    for (px, py), col in zip(pts, colors):
        o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + px * scale), Inches(y + py * scale), Inches(r), Inches(r))
        o.fill.solid(); o.fill.fore_color.rgb = rgb(col); o.line.fill.background()
        etree.SubElement(o._element.spPr, qn("a:effectLst"))


SECTION = [0]


def header(slide, num, title, subtitle=None, dark=False):
    """장 번호(연한 큰 숫자, 자동 증가) + 제목 + 부제. 모티프는 우상단."""
    if num:
        SECTION[0] += 1; num = SECTION[0]
    bg = T["dark"] if dark else T["bg"]
    rect(slide, 0, 0, W, H, bg)
    col_t = T["dark_text"] if dark else T["text"]
    col_m = T["dark_muted"] if dark else T["muted"]
    if num:
        tb(slide, 0.6, 0.42, 1.4, 1.0, f"{num:02d}", size=40, bold=True, color=(T["card2"] if not dark else "2A3160") if THEME != "B" else "1E293B", font="Arial")
    tb(slide, 0.6 if not num else 1.55, 0.55, 9.6, 0.7, title, size=28, bold=True, color=col_t)
    if subtitle:
        tb(slide, 0.6 if not num else 1.55, 1.18, 10.3, 0.5, subtitle, size=14, color=col_m)
    node_motif(slide, 11.55, 0.55, scale=0.9)
    # 페이지 번호
    tb(slide, 12.2, 7.05, 0.8, 0.3, str(len(prs.slides)), size=10, color=col_m, align=PP_ALIGN.RIGHT, font="Arial")
    tb(slide, 0.6, 7.05, 6, 0.3, "역량 경로 추천 — 전공 ↔ 역량 ↔ LG 계열사 신입 직무 지식그래프", size=9, color=col_m)


def card(slide, x, y, w, h, title=None, body=None, fill=None, title_color=None, body_size=12, title_size=14, icon=None):
    rect(slide, x, y, w, h, fill or T["card"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    cy = y + 0.18
    if icon:
        o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.22), Inches(cy - 0.02), Inches(0.42), Inches(0.42))
        o.fill.solid(); o.fill.fore_color.rgb = rgb(title_color or T["primary"]); o.line.fill.background()
        etree.SubElement(o._element.spPr, qn("a:effectLst"))
        tf = o.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = icon
        r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = rgb("FFFFFF"); r.font.name = "Arial"
    if title:
        tb(slide, x + (0.78 if icon else 0.25), cy + 0.03, w - (1.0 if icon else 0.5), 0.4, title, size=title_size, bold=True, color=title_color or T["primary"])
        cy += 0.5
    if body:
        if isinstance(body, list):
            bullets(slide, x + 0.25, cy + 0.05, w - 0.5, h - (cy - y) - 0.2, body, size=body_size)
        else:
            tb(slide, x + 0.25, cy + 0.05, w - 0.5, h - (cy - y) - 0.2, body, size=body_size)


def lesson(slide, text, y=6.25):
    """배운 문장 한 줄 — 코랄 강조 카드."""
    rect(slide, 0.6, y, 12.1, 0.62, T["card2"] if THEME != "B" else "1E293B", MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.3)
    tb(slide, 0.9, y + 0.13, 11.6, 0.4, [[("배운 문장  ", {"bold": True, "color": T["accent"], "size": 14}), (text, {"size": 14, "bold": True})]],
       size=14, anchor=MSO_ANCHOR.MIDDLE)


def table(slide, x, y, w, rows, col_widths, font_size=11, header_fill=None, row_h=0.36, first_col_bold=False, zebra=True):
    nrows, ncols = len(rows), len(rows[0])
    shp = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(row_h * nrows))
    tbl = shp.table
    tblPr = tbl._tbl.tblPr; tblPr.set("bandRow", "0"); tblPr.set("firstRow", "0")
    # 기본 스타일 제거
    style = tblPr.find(qn("a:tableStyleId"))
    if style is not None: tblPr.remove(style)
    for ci, cw in enumerate(col_widths):
        tbl.columns[ci].width = Inches(cw)
    for ri, row in enumerate(rows):
        tbl.rows[ri].height = Inches(row_h)
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.margin_left = cell.margin_right = Inches(0.08); cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if ri == 0:
                cell.fill.fore_color.rgb = rgb(header_fill or T["primary"])
            else:
                cell.fill.fore_color.rgb = rgb(T["card"] if (zebra and ri % 2 == 0) else (T["bg"] if THEME != "B" else "172033"))
            tcPr = cell._tc.get_or_add_tcPr()
            for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
                ln = etree.SubElement(tcPr, qn(tag)); ln.set("w", "6350"); ln.set("cap", "flat"); ln.set("cmpd", "sng")
                sf = etree.SubElement(ln, qn("a:solidFill")); c = etree.SubElement(sf, qn("a:srgbClr")); c.set("val", "FFFFFF" if ri == 0 else ("D9DCE3" if THEME != "B" else "334155"))
            tf = cell.text_frame; tf.word_wrap = True
            runs = val if isinstance(val, list) else [(str(val), {})]
            p = tf.paragraphs[0]
            for rtext, opts in runs:
                r = p.add_run(); r.text = rtext; f = r.font; f.name = FONT; f.size = Pt(opts.get("size", font_size))
                f.bold = opts.get("bold", ri == 0 or (first_col_bold and ci == 0))
                f.color.rgb = rgb(opts.get("color", ("FFFFFF" if ri == 0 else T["text"])))
    return shp


def mono(slide, x, y, w, h, text, size=10.5, fill=None):
    rect(slide, x, y, w, h, fill or T["card"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.03)
    lines = text.split("\n")
    box = slide.shapes.add_textbox(Inches(x + 0.2), Inches(y + 0.15), Inches(w - 0.4), Inches(h - 0.3))
    tf = box.text_frame; tf.word_wrap = False
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, l in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.05
        r = p.add_run(); r.text = l if l else " "
        r.font.name = T["mono"]; r.font.size = Pt(size); r.font.color.rgb = rgb(T["text"])
    return box


def callout(slide, x, y, w, text, color=None, size=11):
    """작은 말풍선 캡션 (카드 옆 화살표 설명)."""
    rect(slide, x, y, w, 0.42, color or T["accent"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.4)
    tb(slide, x + 0.15, y + 0.08, w - 0.3, 0.3, text, size=size, bold=True, color="FFFFFF", anchor=MSO_ANCHOR.MIDDLE)


def trial_slide(num, title, lesson_text, cols, sub=None):
    """시행착오 슬라이드 공통 틀: 4열(증상/원인/알아챈 방법/바꾼 것) + 배운 문장."""
    s = prs.slides.add_slide(BLANK)
    header(s, num, title, sub)
    labels = ["증상", "원인", "어떻게 알아챘나", "바꾼 것"]
    icons = ["!", "?", "👁", "→"]
    colors = [T["accent"], T["accent"], T["primary"], T["good"]]
    cw, gap, x0, y0 = 2.85, 0.23, 0.6, 1.85
    for i, (lab, body) in enumerate(zip(labels, cols)):
        x = x0 + i * (cw + gap)
        card(s, x, y0, cw, 4.0, title=lab, body=body, title_color=colors[i], body_size=11.5, icon=icons[i] if icons[i] != "👁" else "◉")
    lesson(s, lesson_text, y=6.15)
    s.notes_slide.notes_text_frame.text = f"[{title}] 증상 → 원인 → 어떻게 알아챘나 → 바꾼 것 순서로 1분. 마지막에 배운 문장 한 줄을 그대로 읽는다: {lesson_text}"
    return s


# ════════════════════════════════════════════════════════════════════
# 1. 표지 (dark)
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, W, H, T["dark"])
node_motif(s, 9.6, 1.1, scale=2.6, colors=[T["primary"] if THEME == "B" else "5B6BC4", T["accent"], "5B6BC4" if THEME != "B" else T["primary"]])
tb(s, 0.9, 1.5, 8.6, 0.5, "LG CNS AI캠퍼스 · Knowledge Graph 과정 · 3주차 미니 프로젝트", size=14, color=T["dark_muted"])
tb(s, 0.9, 2.1, 9.2, 1.9, [[("역량 경로 추천", {"size": 44, "bold": True, "color": T["dark_text"]})],
                           [("전공 ↔ 역량 ↔ LG 계열사 신입 직무 지식그래프", {"size": 24, "color": T["dark_text"]})]], size=24)
tb(s, 0.9, 4.15, 9.5, 1.0, [[("\"좋아하는 것\"에서 \"첫 직장\"까지 — ", {"size": 18, "color": T["dark_muted"]}),
                            ("지어내지 않고 데이터로 잇기", {"size": 18, "bold": True, "color": T["accent"]})]], size=18)
tb(s, 0.9, 5.6, 9.5, 0.9, [[("무엇을 만들었나보다 ", {"size": 14, "color": T["dark_muted"]}), ("무엇이 틀렸고 어떻게 알아챘나", {"size": 14, "bold": True, "color": T["dark_text"]}),
                            ("에 대한 발표입니다", {"size": 14, "color": T["dark_muted"]})],
                           [("팀 4명 · 2026-09-14 ~ 09-18 · 서울대 교육과정 × LG 채용 공고 · 발표 2026-09-18", {"size": 12, "color": T["dark_muted"]})]], size=14)

# ════════════════════════════════════════════════════════════════════
# 2. 구성 — 시행착오 6개
s = prs.slides.add_slide(BLANK)
header(s, None, "이 발표의 구성 — 성과 두 장, 시행착오 여섯 장", "각 시행착오는 같은 틀로: 증상 → 원인 → 어떻게 알아챘나 → 바꾼 것 → 배운 문장 한 줄")
items = [("LLM은 시키면 채운다", "첫 배치 102개 중 22개 · \"없으면 없다\"를 허용하지 않으면 지어낸다"),
         ("글자가 같아야 이어진다", "공통 역량 8개에서 멈춤 → 통제 어휘 + IS_A 한 단계"),
         ("점수식은 정답지로", "점수식 3번 교체 · 평가셋 24건 · 매칭 동결"),
         ("프롬프트 한 단어", "\"명확하게\" 한 단어와 라벨 하나로 결과가 흔들린 이야기"),
         ("대화는 입력, 판정은 도구", "7영역 대화 20회 → 6회 · 더 물으면 더 흔들렸다"),
         ("넷이 한 파일을 고치면", "동시 편집 충돌 3회 · 사라진 28줄 · 문서와 숫자가 구했다")]
for i, (t1, t2) in enumerate(items):
    cx = 0.6 + (i % 3) * 4.1; cy = 2.0 + (i // 3) * 2.0
    card(s, cx, cy, 3.85, 1.7, title=t1, body=t2, body_size=12, title_size=15, icon=str(i + 1))
tb(s, 0.6, 6.25, 12, 0.4, "앞뒤로: 무엇을 만들었나(30초 데모·재료) · 챗봇 대조 실험 · 한계 · 다른 팀에 묻고 싶은 것", size=12, color=T["muted"])

# ════════════════════════════════════════════════════════════════════
# 3. 무엇을 만들었나 — 한 문장 + 흐름
s = prs.slides.add_slide(BLANK)
header(s, 1, "무엇을 만들었나 — 한 문장", "고등학생이 \"이런 걸 좋아하고 잘해요\"라고 말하면, \"이 전공에 가서 이 과목을 듣고 LG의 이 일을 할 수 있어요\"라고 근거와 함께 답한다")
steps = [("학생의 이야기", "자기소개 · 대화\n또는 질문 3개", T["muted"]), ("역량 태그", "사전에 있는 단어로만\n예) 데이터 분석, 통계", T["primary"]),
         ("전공 1위", "전공 61개 전부 비교\n예) 통계학과", T["primary"]), ("직무", "전공이 기르는 역량으로\n예) LGES 소재개발AX", T["primary"]),
         ("과목 3개", "전공과 직무를 잇는 다리\n예) 데이터마이닝", T["good"])]
bx, by, bw, bh, bg_ = 0.6, 2.2, 2.2, 1.6, 0.35
for i, (t1, t2, col) in enumerate(steps):
    x = bx + i * (bw + bg_)
    rect(s, x, by, bw, bh, T["card"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + bw / 2 - 0.2), Inches(by - 0.22), Inches(0.4), Inches(0.4))
    o.fill.solid(); o.fill.fore_color.rgb = rgb(col); o.line.fill.background(); etree.SubElement(o._element.spPr, qn("a:effectLst"))
    tb(s, x + 0.15, by + 0.35, bw - 0.3, 0.4, t1, size=15, bold=True, color=T["text"], align=PP_ALIGN.CENTER)
    tb(s, x + 0.15, by + 0.8, bw - 0.3, 0.7, t2, size=11, color=T["muted"], align=PP_ALIGN.CENTER)
    if i < len(steps) - 1:
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x + bw + 0.03), Inches(by + bh / 2), Inches(x + bw + bg_ - 0.03), Inches(by + bh / 2))
        c.line.color.rgb = rgb(T["muted"]); c.line.width = Pt(2)
tb(s, 0.6, 4.2, 12, 0.4, "지도(지식그래프) 위에서만 답을 찾는다", size=16, bold=True, color=T["primary"])
card(s, 0.6, 4.7, 5.9, 1.5, title="판정은 도구가 한다", body="전공 순위·직무·과목은 사전 찾기와 집합 계산(겹치는 것 세기)으로만. 같은 이야기 → 같은 답. 카드의 과목·직무는 전부 데이터에 실제로 있는 것", body_size=12, icon="=")
card(s, 6.8, 4.7, 5.9, 1.5, title="LLM은 두 곳에만", body="① 글에서 역량 이름 뽑기(지도 만들 때 277번, 학생 이야기에서 1번)  ② 카드를 친절한 문단으로 풀어 쓰기(1번). 판정에는 관여하지 않는다", body_size=12, icon="AI")

# ════════════════════════════════════════════════════════════════════
# 4. 30초 데모 — 카드
s = prs.slides.add_slide(BLANK)
header(s, 2, "30초 데모 — 학생에게 보이는 카드", "입력: \"데이터 분석이 재미있어요 / 통계 수업, 파이썬으로 데이터 정리\"  (시연 대본 세트 1, 실제 출력)")
card_text = """[프로필]  Data Analysis · Statistics · Python

[전공]    통계학과
          선택 이유: 전체 61개 전공 중 보유 역량과 관련된 46개를 선정,
          그 중 1위가 통계학과
          ✓ Data Analysis (과목 7개) · Statistics (과목 14개)
          ○ 아직 안 이어진 역량 — Python
          역량 연결도
            █████░░░░░  46%  통계학과
            ████░░░░░░  39%  화학생물공학부
            ████░░░░░░  38%  첨단융합학부

[과목]    통계학과에서 이 역량을 기르는 과목
          기계학습과 계산금융 → Machine Learning 역량 향상
          데이터마이닝 방법 및 실습 → Data Analysis 역량 향상
          다변량자료분석 및 실습 → Data Analysis 역량 향상

[직무]    LG에너지솔루션 소재개발AX (신입)
          요구 역량 2/2 충족
          Data Analysis(O), Machine Learning(O)

[다음 후보]
          1. LG CNS AI (AX) (신입) — 요구 역량 7/10 충족 …
──────────
출처 · 과목: 서울대학교 교육과정 — 대학알리미 · 공고: LG Careers (스냅샷)"""
mono(s, 0.6, 1.8, 7.9, 5.15, card_text, size=10)
callout(s, 8.8, 2.35, 4.0, "① 61개 전공 전부 비교 — 전수 순위")
tb(s, 8.8, 2.82, 4.0, 0.6, "떠오른 서너 개 중에 고르는 챗봇과 다른 첫 줄", size=11, color=T["muted"])
callout(s, 8.8, 3.45, 4.0, "② ✓ 이어진 것 · ○ 안 이어진 것", color=T["good"])
tb(s, 8.8, 3.92, 4.0, 0.6, "안 이어진 역량(Python)도 숨기지 않는다. 46%는 \"어울릴 확률\"이 아니라 역량 연결도", size=11, color=T["muted"])
callout(s, 8.8, 4.75, 4.0, "③ 실존하는 과목·직무 + 출처", color=T["primary"])
tb(s, 8.8, 5.22, 4.0, 0.9, "카드의 모든 고유명사는 3,829개 과목·172개 직무 데이터에 있다 — 매 실행 자동 확인. 이 아래에 LLM이 쓴 [진로 추천] 문단이 붙는다", size=11, color=T["muted"])

# ════════════════════════════════════════════════════════════════════
# 5. 재료와 지도 — 숫자
s = prs.slides.add_slide(BLANK)
header(s, 3, "재료와 지도 — 숫자 여덟 개", "실제 대학 교육과정과 실제 채용 공고. 지어낼 재료를 주지 않으려면 진짜 재료가 있어야 한다")
stats = [("105", "서울대 전공", "과목 3,829개 (대학알리미 공시)"), ("9곳", "LG 계열사", "공고 50건 → 직무 172개 (신입 85)"),
         ("61·120·108", "전공 · 역량 · 직무 노드", "관계 5종 · IS_A 102개"), ("139", "통제 어휘 대표 표기", "별칭 417개 · 상위 개념 23개"),
         ("277회", "지도 만들 때 AI 호출", "한 번만 · 결과는 캐시 (그 뒤 0회)"), ("2~6회", "학생 1명당 AI 호출", "판정에는 0회 — 추출과 표현에만"),
         ("24 / 24", "정답지(평가셋) 통과", "IT 10 · 비IT 10 · 대화 4 — 매번 자동 채점"), ("3건", "확인 항목", "재현성 · 실존 · 집합 연산")]
for i, (big, lab, sub) in enumerate(stats):
    cx = 0.6 + (i % 4) * 3.1; cy = 1.95 + (i // 4) * 2.35
    rect(s, cx, cy, 2.85, 2.1, T["card"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    tb(s, cx + 0.2, cy + 0.25, 2.5, 0.8, big, size=24 if len(big) > 8 else 36, bold=True, color=T["primary"], font="Arial")
    tb(s, cx + 0.2, cy + 1.1, 2.5, 0.4, lab, size=13, bold=True, color=T["text"])
    tb(s, cx + 0.2, cy + 1.48, 2.5, 0.55, sub, size=10.5, color=T["muted"])

# ════════════════════════════════════════════════════════════════════
# 6. 어떻게 동작하나 — 지도 만들기 / 지도 읽기
s = prs.slides.add_slide(BLANK)
header(s, 4, "어떻게 동작하나 — 한 번 만들고, 매번 읽는다", "오프라인(배치)과 온라인(실시간)을 완전히 분리 — 비용과 재현성 둘 다 여기서 나온다")
card(s, 0.6, 1.85, 6.0, 3.6, title="지도 만들기 — 미리, 한 번만 (LLM 277회, 캐시)", body=[
    [("과목 이름 3,829개 → AI가 \"이 전공은 이런 역량을 기른다\"", {})],
    [("채용 공고 172개 → AI가 \"이 직무는 이런 역량을 요구한다\"", {})],
    [("같은 말은 같은 이름으로: 사전(통제 어휘) 139개 — ", {}), ("사전에 있는 단어로만 지도를 그린다", {"bold": True})],
    [("\"Oracle은 Database의 한 종류\" — IS_A 102개로 도구 이름과 학문 이름을 잇는다", {})],
    [("원출력은 파일에 저장(캐시) → 규칙을 고칠 때마다 0원으로 다시 필터", {"bold": True})],
], body_size=12, icon="1")
card(s, 6.9, 1.85, 5.8, 3.6, title="지도 읽기 — 학생이 올 때마다 (LLM 2~6회)", body=[
    [("① 이야기 → 역량 태그 (AI 1회, 사전 안의 단어만)", {})],
    [("② 태그 → 전공 순위: 61개 전부 비교, 1위 확정 — ", {}), ("사전 찾기·집합 계산", {"bold": True})],
    [("③ 전공 → 직무: 그 전공이 기르는 역량 전체로 공고와 대조 (충족/부족 개수)", {})],
    [("④ 전공·직무 → 과목: 둘을 잇는 역량을 기르는 과목 3개", {})],
    [("⑤ 카드 + AI가 쓴 설명 문단(1회) — 카드에 없는 건 쓰지 않도록 규칙", {})],
], body_size=12, icon="2")
lesson(s, "판정(②③④)에 LLM이 없어서 같은 이야기에 같은 답이 나오고, 카드의 이름은 전부 실존한다.", y=5.75)

# ════════════════════════════════════════════════════════════════════
# 6-2. 기술 스택
s = prs.slides.add_slide(BLANK)
header(s, 5, "기술 스택 — 작게, 표준으로", "Python 3,100줄 · 파일 7개 · 외부 의존성 5개. \"판정은 도구가 한다\"를 지키려면 도구가 단순해야 했다")
stack = [
    ("언어 · 협업", "Py", [
        [("Python 3.14", {"bold": True}), (" — 코드 3,100줄(팀 모듈 포함 4,500), 파일 7개", {})],
        [("Git · GitHub", {"bold": True}), (" — 커밋 167 · PR 15 · 브랜치 전략(기능 브랜치 → PR)", {})],
        [("VS Code · Claude Code", {"bold": True}), (" — 팀원 2명이 코딩 보조로 사용 (동시 편집 사고의 원인이자 문서화의 도구)", {})]]),
    ("LLM", "AI", [
        [("OpenAI gpt-4o-mini", {"bold": True}), (", temperature 0 — 추출·태거·설명 문단 전부 같은 모델", {})],
        [("LangChain", {"bold": True}), (" — ChatPromptTemplate · with_structured_output(pydantic) · stream/astream", {})],
        [("pydantic", {"bold": True}), (" — 출력 스키마(Tags · MajorSkills · JobExtraction · StudentProfile). Literal 로 라벨 고정", {})]]),
    ("데이터 · 수집", "DB", [
        [("requests", {"bold": True}), (" — LG Careers 내부 API(JSON) 호출, 날짜별 스냅샷 data/raw/", {})],
        [("pandas", {"bold": True}), (" — 대학알리미 CSV(3,829행)를 전공 단위로 그룹화", {})],
        [("JSON 파일 3층", {"bold": True}), (" — raw(LLM 원출력 캐시) → extracted(필터) → graph.json. DB 없음", {})]]),
    ("지식그래프", "KG", [
        [("graph.json + Python dict/set", {"bold": True}), (" — 노드 5종·관계 5종, 집합 연산으로 판정 (LLM 0회)", {})],
        [("vocab.py", {"bold": True}), (" — 통제 어휘 139 · IS_A 102 · 성향→역량 7 · 성향→태도 17 (사람이 관리하는 온톨로지)", {})],
        [("의도적으로 뺀 것: Neo4j · 벡터 임베딩", {"bold": True, "color": T["accent"]}), (" — 노드 300개 규모라 dict 로 충분. Cypher 로 옮길 수 있게 설계 (확장 과제)", {})]]),
    ("화면", "UI", [
        [("CLI", {"bold": True}), (" — app.py 입력 4방식(--basic · --interview · 기본 대화 · --profile) + 역방향 --job", {})],
        [("Flask + Jinja", {"bold": True}), (" — index.html(채팅) · details.html(문단). 판정은 여기서 하지 않는다", {})],
        [("SSE(EventSource)", {"bold": True}), (" — 설명 문단 스트리밍. 카드는 즉시, 문단은 흘려보냄", {})]]),
    ("검증 · 문서", "QA", [
        [("check.py", {"bold": True}), (" — 확인 3건 + 평가셋 24건(JSON) 자동 채점, 대본 주입(ask/say)으로 대화도 자동", {})],
        [("tiktoken", {"bold": True}), (" — 토큰 실측(115k vs 1.4k). 감으로 말하지 않기 위해", {})],
        [("Markdown + Mermaid", {"bold": True}), (" — 설명서 1,200줄 · 결정 기록 12개 · 시연 대본 · 챗봇 대조 실험", {})]]),
]
for i, (t1, ic, body) in enumerate(stack):
    cx = 0.6 + (i % 3) * 4.1; cy = 1.8 + (i // 3) * 2.5
    card(s, cx, cy, 3.85, 2.38, title=t1, body=body, body_size=10.5, title_size=14, icon=ic, title_color=T["accent"] if ic == "KG" else T["primary"])
tb(s, 0.6, 6.78, 12, 0.3, "requirements.txt 5줄: flask · langchain-core · langchain-openai · python-dotenv · pydantic (+ pandas · requests · tiktoken)", size=10.5, color=T["muted"])

# ════════════════════════════════════════════════════════════════════
# 6-3. 지난주 수업 → 이번 프로젝트 (LLM 서비스 설계 6요소)
s = prs.slides.add_slide(BLANK)
header(s, 6, "지난주 수업이 어디에 쓰였나 — 설계 6요소", "9/8~9/11 (RCIF · 프롬프트 템플릿 · LCEL · Pydantic · Function Calling · 상태 관리) → 이 프로젝트의 어느 파일")
rows = [["요소 (9/11 수업)", "수업에서 배운 것", "이 프로젝트에서는", "어디에"],
        ["① 프롬프트 ★", "RCIF · Zero/Few-shot · v1→v4 반복(작성→테스트→관찰→수정) · 프롬프트 템플릿 {변수}", "시스템 프롬프트 3종을 RCIF로. 실제 오류 4건을 음성 예시로, 정상 3건을 양성 예시로(Few-shot). 전공 추출 v1→v3 재작성", "build_graph_majors.py · transform_v2.py · app.py"],
        ["② 체인 구조", "LCEL 파이프: 프롬프트 | 모델 | 파서, invoke/stream/batch", "체인 8개 전부 `프롬프트 | llm.with_structured_output(스키마)`. 온라인은 순서가 고정된 파이프라인(태거 → 도구 → 설명)", "app.py · interview.py · user_analysis/"],
        ["③ 도구 목록", "Function Calling: @tool + bind_tools — \"AI는 판단, 도구가 실행\"", "배운 대로 하지 않았다: LLM이 도구를 고르게 할 이유가 없어(순서 고정) 판정 자체를 도구(graph_store 4함수·사전 조회)에 넘김. bind_tools 0회", "graph_store.py · vocab.py"],
        ["④ 상태 관리", "LLM은 stateless. 히스토리는 dict로, 전략은 Sliding/Summary/Entity/Vector", "대화 상태는 서버 dict(InterviewSession). 대화 전체 대신 요약된 프로필(pydantic)을 들고 다닌다 = Summary Memory 방식", "interview.py · webapp.py"],
        ["⑤ 스트리밍", "stream() — 완성된 토큰을 즉시 출력, 사용성", "설명 문단만 astream/stream → 웹 SSE. 카드(판정)는 즉시, 문단은 흘려보냄", "app.py explain · webapp.py"],
        ["⑥ 비용·지연", "호출 수·토큰을 세어 설계에 반영", "오프라인 277회 1회성 캐시 · 온라인 2~6회 · tiktoken 실측(115k vs 1.4k) · 대화 20회→6회", "docs/발표_수치 · check.py"]]
table(s, 0.6, 1.85, 12.1, rows, [1.7, 3.3, 4.6, 2.5], font_size=10, row_h=0.62, first_col_bold=True)
lesson(s, "다섯은 배운 대로, 도구 하나는 뒤집어서 — AI가 도구를 고르는 게 아니라 판정을 도구가 한다.", y=6.38)

# ════════════════════════════════════════════════════════════════════
# 6-4. 프롬프트 전략 — RCIF 를 실제 프롬프트에
s = prs.slides.add_slide(BLANK)
header(s, 7, "프롬프트 전략 — RCIF를 실제 프롬프트에", "전공 역량 추출 프롬프트(build_graph_majors.py EXTRACT_SYSTEM) 발췌. 직무 추출·태거·설명 문단도 같은 틀")
prompt_lines = [
    ("R", "너는 대학 교육과정을 분석해 전공이 기르는 역량을 판별하는 전문가다."),
    ("C", "입력: 전공명 + 그 전공의 개설 과목명 목록 / 출력: 이 전공이 기르는 역량 + 근거 과목명"),
    ("C", "[통제 어휘 목록] {vocab_list}      ← 프롬프트 템플릿 변수. 사전 139개가 그대로 들어간다"),
    ("I", "1. skill 은 통제 어휘 목록에 있는 것만. 목록에 없는 역량은 만들지 않는다"),
    ("I", "2. via 는 준 과목명을 그대로. 줄이거나 바꾸지 않는다"),
    ("I", "4. 해당하는 역량이 없으면 빈 배열이 정답이다. 억지로 채우지 마라"),
    ("F", "[이런 건 틀린 답이다 — 실제로 나왔던 오류]  ✗ 간호학과 '의료관련감염관리' → Security"),
    ("F", "[이런 건 맞는 답이다]  ✓ 통계학과 '회귀분석 및 실습' → Statistics"),
    ("F", "class MajorSkills(BaseModel): skills: list[...] = Field(max_length=10)  # 형식은 스키마가"),
]
rect(s, 0.6, 1.85, 7.6, 4.55, T["card"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.03)
colmap = {"R": T["primary"], "C": T["good"], "I": T["accent"], "F": "7C3AED" if THEME != "B" else "C4B5FD"}
for i, (tag, line) in enumerate(prompt_lines):
    y = 2.0 + i * 0.47
    o = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(y + 0.03), Inches(0.38), Inches(0.3)); o.adjustments[0] = 0.3
    o.fill.solid(); o.fill.fore_color.rgb = rgb(colmap[tag]); o.line.fill.background(); etree.SubElement(o._element.spPr, qn("a:effectLst"))
    tf = o.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    pp = tf.paragraphs[0]; pp.alignment = PP_ALIGN.CENTER; r = pp.add_run(); r.text = tag; r.font.bold = True; r.font.size = Pt(11); r.font.color.rgb = rgb("FFFFFF"); r.font.name = "Arial"
    tb(s, 1.3, y + 0.02, 6.8, 0.4, line, size=10.5, color=T["text"], font=T["mono"] if tag == "F" and "class " in line else FONT)
tb(s, 0.8, 6.45, 7.4, 0.3, "R 역할 · C 맥락(입력·출력·사전) · I 지시(규칙) · F 형식(예시 + pydantic) — 수업 9/8 RCIF, 9/9 구조화 출력", size=10, color=T["muted"])
card(s, 8.5, 1.85, 4.2, 1.4, title="Few-shot은 우리 오류로", body="수업: \"복잡한 기준·일관된 출력이면 퓨샷\". 예시를 지어내지 않고 9/14 실제 오분류 4건(간호학과→Security …)을 음성 예시로, 정상 3건을 양성 예시로", body_size=10.5, icon="✗", title_color=T["accent"])
card(s, 8.5, 3.4, 4.2, 1.4, title="v1 → v3, 그리고 정답지", body="수업: \"작성→테스트→관찰→수정, v4를 했다고 끝이 아니다\". 전공 추출 프롬프트를 세 번 다시 썼고, '끝이 아닌' 부분을 평가셋 24건으로 대신했다", body_size=10.5, icon="↻")
card(s, 8.5, 4.95, 4.2, 1.45, title="Format = 스키마, 개수는 근거가", body="수업: with_structured_output은 모델 수준에서 형식을 강제. 그래서 Format을 글이 아니라 pydantic으로. 단 max_length만 두고 하한은 없앴다 — 개수를 시키면 채운다(4회 관측)", body_size=10.5, icon="{}", title_color=T["good"])

# ════════════════════════════════════════════════════════════════════
# 7~12. 시행착오 6개
trial_slide(5, "시행착오 ① — LLM은 시키면 채운다", "LLM에게 \"없다\"라고 말할 권리를 주지 않으면, 있는 것처럼 말한다.",
    sub="9/14 밤, 전공 102개 첫 배치 — 그리고 같은 뿌리의 사례 네 번",
    cols=[
        [[("102개 중 22개만 역량이 잡힘", {"bold": True})], "컴퓨터공학부 = Security 하나", "간호학과 = Security, Cloud", "통계학과 = 빈 리스트", "전공·직무 공통 역량 3개 → 추천 불가"],
        ["\"근거 과목 2개 이상\" 규칙 — 대학 과목은 주제당 1개", "과목명 정확 일치 — '기계학습 개론'을 '기계학습'으로 줄이면 무효", [("\"없으면 빈 배열이 정답\"이 없었다", {"bold": True}), (" → 간호학과에도 무언가를 붙임", {})], "대표 표기 자기 이름이 사전 조회에서 탈락"],
        ["결과 파일을 눈으로 열어 봤다 — \"컴공 = Security 하나\"는 누가 봐도 이상", [("같은 뿌리 4회 더: ", {"bold": True}), ("\"정확히 3개\" → Cloud를 채움 · \"4~8개\" · \"최대 5개\" · \"3문장 이상\" → 없는 직무 업무를 상상", {})]],
        ["근거 1개면 채택, 부분 일치 허용", "프롬프트에 음성 예시 4건 + \"없으면 []\"", [("개수 지시 전부 삭제 — ", {}), ("\"근거가 1개면 1개만\"", {"bold": True})], [("LLM 호출과 필터를 분리, 원출력 캐시(3층 보관)", {"bold": True}), (" → 이후 재추출은 0원", {})]],
    ])

trial_slide(6, "시행착오 ② — 글자가 같아야 이어진다", "온톨로지는 거창한 게 아니라 \"A는 B의 한 종류\" 100줄이었다. 대신 방향(위로만)을 지키는 게 전부.",
    sub="9/15 낮, 전공·직무 공통 역량이 8개에서 멈췄다",
    cols=[
        ["어휘를 정리해도 전공·직무 공통 역량 8개", [("직무: ", {"bold": True}), ("Java, React, AWS, Oracle (도구 이름)", {})], [("전공: ", {"bold": True}), ("Programming, Database, Cloud (학문 이름)", {})], "같은 뜻인데 글자가 달라 선이 안 이어짐"],
        ["평평한(flat) 사전 — 표기만 통일하고 개념 사이 관계가 없었다", "LG 계열사로 넓혀도 어휘가 안 겹치는 계열사는 노드만 늘고 추천은 안 늘었다 (LGES 초기 실측)"],
        ["빌더 리포트의 \"양쪽 공통 Skill\" 숫자 — 8에서 안 움직였다", "직무 쪽 상위 역량 목록과 전공 쪽 목록을 나란히 놓고 보니 층이 달랐다"],
        [[("IS_A 한 단계 102개: ", {"bold": True}), ("\"Oracle은 Database의 한 종류\"", {})], "규칙 ① 한 단계만 (두 단계면 모든 전공이 모든 직무와 이어져 변별력 0)", "규칙 ② 부모도 과목명에 근거 있는 말만", [("규칙 ③ 추론은 위로만 ", {"bold": True}), ("— 전공이 Database를 가르친다고 Oracle을 안다고 말하지 않는다", {})], "공통 8 → 22 → 30, 이어지는 직무 역량 0 → 75. 어휘 3단계로 비IT까지: 신입 직무 52 → 75"],
    ])

s = prs.slides.add_slide(BLANK)
header(s, 7, "시행착오 ③ — 점수식은 눈이 아니라 정답지로", "점수식을 세 번 바꿨고, 매번 \"이상한 1위\"가 알려줬다. 바뀐 건 점수식보다 알아채는 방법이었다")
rows = [["버전", "증상 (이상한 1위)", "원인", "수정"],
        ["집합 코사인", "\"데이터 분석·통계\"에 식물생산과학부·의예과가 1.0 공동 1위, 통계학과 0.82", "역량이 적은 전공이 이긴다", "커버리지 — 학생 태그 중 채운 비율"],
        ["idf 가중", "Programming(idf 3.0)을 1과목만 가진 전공이 통계학과(근거 19과목)를 이김", "드문 역량이 너무 셈", "√idf × 근거 강도 (과목 3개면 만점)"],
        ["직무 코사인", "'영업마케팅: Data Analysis 1개' 직무가 항상 만점", "역량 1개짜리 공고", "역량 2개 이상만 그래프에"],
        ["동점 처리", "0.4763 / 0.4714가 반올림 경계에서 갈림", "반올림으로 동점을 묶음", "인접 0.01 안이면 동점 → 태도 적합으로"]]
table(s, 0.6, 1.85, 12.1, rows, [1.6, 4.6, 2.6, 3.3], font_size=11, row_h=0.62, first_col_bold=True)
card(s, 0.6, 5.05, 5.9, 1.1, title="알아채는 방법이 바뀌었다", body="눈으로 서너 개 보고 고치기 → 고칠 때마다 다른 데가 깨짐 → 정답지 10건 → 24건(비IT 10, 대화 4)", body_size=11.5, icon="◉")
card(s, 6.8, 5.05, 5.9, 1.1, title="정답지가 실제로 잡은 것 (2회)", body="\"새 단어 하나 넣었더니 엉뚱한 직무가 1위\" — HSAD 미디어 ← '데이터 분석 툴', 디지털 기획 ← Tableau/GA. 이후 매칭 동결", body_size=11.5, icon="✓", title_color=T["good"])
lesson(s, "고치기 전에 정답지를 먼저 쓴다. 정답지가 없으면 \"고쳤다\"와 \"옮겼다\"를 구분할 수 없다.", y=6.3)

trial_slide(8, "시행착오 ④ — 프롬프트 한 단어", "결정(약점을 쓰지 않는다)과 구현(그 단어를 지운다)은 다른 일이었다. 첫 진단은 틀렸고, diff가 맞았다.",
    sub="9/16 저녁, 인터뷰 평가 4건이 실행마다 2/4 ↔ 3/4",
    cols=[
        ["같은 자기소개인데 강점 성향이 실행마다 다름 — 발표력·설득력 ↔ 분석성만", "그래서 \"요구 태도 ✓\"가 떴다 안 떴다", "1위 전공도 컴퓨터공학부 ↔ 건설환경도시공학부"],
        [[("첫 진단(틀림): ", {"bold": True, "color": T["accent"]}), ("\"규칙 101줄이 지워졌다\"", {})], [("실행 시점 프롬프트를 두 버전에서 뽑아 diff → 차이는 약점 관련 줄뿐", {"bold": True})], "① 규칙 문구 \"강점으로 나타남\" → \"강점으로 명확하게 나타남\" (문턱 상승)", "② 방향 라벨 3개 → 2개: 경계 성향이 neutral로 몰림"],
        ["실험 3회 — 가중치 3설정 / 옛 프롬프트 / 라벨만 복원", "가중치는 원인이 아니었다 (같은 입력이면 세 설정 결과 동일)", "라벨 3개 + 문구 원복 → 두 번 연속 4/4"],
        [[("약점 \"영역\"(질문·프로필)은 삭제, \"라벨\"은 유지", {"bold": True})], "규칙 8번 원문 복원 (\"명확하게\" 삭제)", [("temperature 0도 완전히 결정적이지 않다 → 프롬프트를 바꾸면 check.py 두 번", {"bold": True})]],
    ])

trial_slide(9, "시행착오 ⑤ — 대화는 입력, 판정은 도구", "더 많이 물으면 더 잘 아는 게 아니라, 더 많이 흔들렸다.",
    sub="질문 3개(고정) → 팀원의 자기소개 분석 모듈 → 7영역 적응형 대화",
    cols=[
        ["7영역 대화: 8라운드 · LLM 20회 · 25초", "\"잘 모르겠어요\" 뒤에 같은 질문을 같은 문장으로 되물음", [("같은 자기소개가 짧은 인터뷰에선 통계학과, 긴 대화에선 컴퓨터공학부", {"bold": True})]],
        ["영역당 2회 상한 + 질문 생성 temperature 0.3", "대화가 길수록 관심 태그가 늘어(파이썬·프로그래밍) 1위가 흔들림", "매칭에 쓰는 건 관심·강점 두 영역뿐인데 일곱 영역을 다 물었다"],
        ["빈 자기소개로 실측 (라운드·호출 수·시간을 셌다)", "평가셋에 대화 케이스 4건 추가"],
        ["되묻기 영역당 1회", [("부족 영역 질문은 관심·강점만 → 2~3라운드 · 6~8회", {"bold": True})], "Q3 객관식 → 프로필로 성향 판단 (LLM 1회)", [("지킨 선: 대화 안에서 LLM이 전공·직무를 말하지 않는다", {"bold": True}), (" — 그 순간 챗봇과 같아진다", {})]],
    ])

trial_slide(10, "시행착오 ⑥ — 넷이 한 파일을 고치면", "역할을 나눠도 파일은 겹친다. 결정 기록(문서)과 회귀 숫자(리포트)가 없었으면 누가 맞는지 다투다 끝났을 것이다.",
    sub="9/16~17, 같은 날 같은 파일을 두 사람이 — 세 번",
    cols=[
        ["어휘 파일을 두 사람이 같은 날 확장 → IS_A 부모 28줄이 통째로 사라짐", "PR 하나가 카드를 디버그 뒤로 숨김 → 차별점이 화면에서 증발", "웹 피드백 4건을 두 세션이 동시 구현 → 같은 함수 충돌 2회", "카드↔문단 순서를 두 사람이 다르게 이해 → 화면 두 번 뒤집힘"],
        ["\"한 사람이 관리\"라고 정했지만 급하면 다들 고친다", "Claude Code로 편집하다 블록이 날아가도 assert는 통과 (이름만 검사)", "머지 범위를 잘못 이해 (\"설명서만\" → 브랜치 전체)"],
        [[("빌더 리포트의 \"IS_A 한 홉 연결\" 숫자가 61 → 43", {"bold": True}), (" — 회귀 감지기", {})], "설명서 2절 \"왜 카드가 있어야 하나\"를 근거로 되돌림", "재생성 실측 표(채택/조정/미채택)로 합의"],
        ["통합 원칙: 팀 요청 형식은 내용으로, 구조 개선은 틀로", "결정은 날짜 문서로 남긴다 (docs/2026091*_*.md 8개)", [("코드와 데이터를 따로 커밋, pull 먼저", {"bold": True})], "빌더를 돌린 뒤 숫자 6개를 눈으로 본다"],
    ])

# ════════════════════════════════════════════════════════════════════
# 13. 챗봇 대조 실험
s = prs.slides.add_slide(BLANK)
header(s, 11, "챗봇 대조 — 같은 자기소개를 세 챗봇에게", "ChatGPT · 뤼튼 · Gemini. 웹 검색 끄고, 임시 채팅으로, 우리 인터뷰 세트 4와 같은 문장 (9/17, 팀 3명이 각각)")
card(s, 0.6, 1.85, 3.9, 2.95, title="ChatGPT (5.6) — 비웠다", body=[
    [("\"'전체 N개 중 1위', '실제 개설 과목 3개', '실제 채용공고의 요구 역량 N개', '출처 URL'은 … 웹 검색 없이 정확성을 보장할 수 없습니다.\"", {"italic": True})],
    [("우리 카드 네 줄과 1:1로 빈칸", {"bold": True})],
    [("과목 3개는 실재 — 단 \"검증하지 않았습니다\"", {})],
], body_size=11, icon="?", title_color=T["muted"])
card(s, 4.7, 1.85, 3.9, 2.95, title="뤼튼 — 채웠다", body=[
    [("과목 3개 중 2개는 3,829개 과목에 없음", {"bold": True, "color": T["accent"]}), (" (1개는 다른 과)", {})],
    [("\"LG CNS 데이터 분석 직무를 추천해! 실제로 이 직무에서 요구하는 …\" — 우리 스냅샷 CNS 신입 9개 직무에 없음", {"italic": True})],
    [("추궁하자: \"실제 특정 출처에서 가져온 게 아니라\"", {})],
], body_size=11, icon="!", title_color=T["accent"])
card(s, 8.8, 1.85, 3.9, 2.95, title="우리 카드 — 세어서 보여준다", body=[
    [("61개 중 46개 비교, 1위 · ✓ Data Analysis (과목 7개) · 요구 2/2 충족 · 출처 대학알리미·LG Careers", {"bold": True})],
    [("매 실행 확인 3건 · 정답지 24건 통과", {})],
    [("챗봇이 잘한 것: 해석과 문장 — 그 부분은 우리도 LLM에 맡긴다(설명 문단)", {})],
], body_size=11, icon="✓", title_color=T["good"])
rows = [["항목", "우리 카드", "ChatGPT", "뤼튼", "Gemini"],
        ["전수 순위 \"N개 중 1위\"", "61개 중 46개 비교, 1위", "✗ \"답하지 않겠습니다\"", "✗ 3개 나열, 순위 없음", "✗ 3행 표, 순위 없음"],
        ["과목명 실재", "✓ 3,829개 csv 근거", "실재하나 \"검증 안 함\"", "3개 중 2개 없음", "8개 중 4개 없음"],
        ["요구 역량 커버/갭", "요구 2개 중 2개 (특정 공고)", "\"7개 중 4개\" — 일반 기준", "출처 없이 단정", "직무명은 근접, 설명은 어긋남"],
        ["재현성 (같은 뜻 다른 말)", "평가셋 매 실행 통과", "1위 유지, 목록·개수 매번 다름", "—", "—"]]
table(s, 0.6, 4.95, 12.1, rows, [2.3, 2.6, 2.5, 2.3, 2.4], font_size=9.5, row_h=0.33)
tb(s, 0.6, 6.7, 12, 0.3, "\"채우거나 비우거나 — 근거 데이터가 있어야 구분된다.\"  전문: docs/20260917_챗봇_대조.md", size=10, color=T["muted"], italic=True)

# ════════════════════════════════════════════════════════════════════
# 14. 비용 — 차트
s = prs.slides.add_slide(BLANK)
header(s, 12, "비용 — 요청 한 번에 LLM이 읽는 토큰", "데이터를 통째로 프롬프트에 넣고 묻는 방식과, 지도를 미리 만들어 두고 읽는 방식")
cd = CategoryChartData()
cd.categories = ["A. 챗봇에 그냥 묻기", "B. 데이터 통째로 넣고 묻기", "C. 우리 (지도 읽기)"]
cd.add_series("요청당 입력 토큰", (500, 115000, 1400))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.85), Inches(7.4), Inches(4.2), cd)
ch = gf.chart; ch.has_legend = False; ch.has_title = True
ch.chart_title.text_frame.text = "요청당 입력 토큰 (gpt-4o-mini 토크나이저 실측)"
ch.chart_title.text_frame.paragraphs[0].runs[0].font.size = Pt(12); ch.chart_title.text_frame.paragraphs[0].runs[0].font.name = FONT
ch.chart_title.text_frame.paragraphs[0].runs[0].font.color.rgb = rgb(T["text"])
plot = ch.plots[0]; plot.has_data_labels = True; plot.gap_width = 60
plot.data_labels.font.size = Pt(11); plot.data_labels.font.name = FONT; plot.data_labels.font.color.rgb = rgb(T["text"])
plot.data_labels.number_format = '#,##0'; plot.data_labels.number_format_is_linked = False; plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
ser = plot.series[0]; ser.format.fill.solid(); ser.format.fill.fore_color.rgb = rgb(T["primary"])
pt = ser.points[2]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(T["good"])
pt = ser.points[1]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(T["accent"])
ch.category_axis.tick_labels.font.size = Pt(11); ch.category_axis.tick_labels.font.name = FONT; ch.category_axis.tick_labels.font.color.rgb = rgb(T["text"])
ch.value_axis.tick_labels.font.size = Pt(9); ch.value_axis.tick_labels.font.color.rgb = rgb(T["muted"]); ch.value_axis.has_major_gridlines = True
ch.value_axis.major_gridlines.format.line.color.rgb = rgb("E5E7EB"); ch.value_axis.tick_labels.number_format = '#,##0'; ch.value_axis.tick_labels.number_format_is_linked = False
ch.category_axis.format.line.color.rgb = rgb("D1D5DB"); ch.value_axis.format.line.fill.background(); ch.category_axis.reverse_order = True
card(s, 8.3, 1.85, 4.4, 1.35, title="≈ 85배", body="B 115,000 vs C 1,400 (태거 464 + 설명 895). 교육과정 67,284 + 신입 공고 48,026 토큰을 매번 읽는 대신 지도를 읽는다", body_size=11, icon="÷")
card(s, 8.3, 3.35, 4.4, 1.35, title="지도 만들기는 1회성 269,000", body="직무 172회 + 전공 105회 = 277회. B의 2.3회분 — 3번째 요청부터 우리가 싸다. 캐시 덕에 그래프를 열 번 넘게 다시 만들며 호출 0회", body_size=11, icon="1")
card(s, 8.3, 4.85, 4.4, 1.2, title="돈보다 큰 이유", body="B는 판정을 LLM이 한다 → 재현성 없음, 개수를 못 센다. 우리는 판정을 도구가 한다", body_size=11, icon="=", title_color=T["accent"])
tb(s, 0.6, 6.35, 12, 0.5, "A는 데이터가 없어 기억으로 답한다(전수 순위·출처 불가). 숫자 근거: docs/20260916_발표_수치_4-5장.md", size=11, color=T["muted"])

# ════════════════════════════════════════════════════════════════════
# 15. 한계
s = prs.slides.add_slide(BLANK)
header(s, 13, "한계 — 솔직하게", "발표에서 먼저 말하는 것이 질문받고 인정하는 것보다 낫다")
lims = [("서울대 1개교", "대학 비교 축이 없다 → \"서울대 교육과정 기준 전공 추천\""), ("과목 이름만", "과목 설명이 없어 이름만 보고 판단. 그래서 전공 단위로 묶어 읽었다"),
        ("공고는 스냅샷", "9/11·9/15에 받은 것. LG CNS 신입 공고는 이미 닫혔다 — 날짜를 붙여 말한다"), ("사전 밖 직무 10건", "신입 85건 중. 어학·오피스 도구만 있는 사무직, 요구 역량 문장이 없는 공고"),
        ("태도 데이터 절반", "108건 중 48건. 빈 값이 \"요구 없음\"인지 \"추출 누락\"인지 몰라 동점 처리에만"), ("LLM 비결정성", "입력 쪽(태그·성향)에서 가끔 흔들린다. 판정은 아니지만 정답지로 계속 감시"),
        ("어학은 점수 밖", "공고 32%가 요구하지만 역량이 아니라 지원 요건. 영어를 \"기르는\" 전공이 과목명엔 없다"), ("문장이 딱딱하다", "판정을 도구에 넘긴 대가. 표현은 LLM 문단이 보완")]
for i, (t1, t2) in enumerate(lims):
    cx = 0.6 + (i % 4) * 3.1; cy = 1.95 + (i // 4) * 2.2
    card(s, cx, cy, 2.85, 1.95, title=t1, body=t2, body_size=11, title_size=13, icon=str(i + 1), title_color=T["muted"] if i % 2 else T["primary"])

# ════════════════════════════════════════════════════════════════════
# 16. 다른 팀에 묻고 싶은 것
s = prs.slides.add_slide(BLANK)
header(s, 14, "다른 팀에 묻고 싶은 것 — 우리가 못 푼 문제 넷", "이 발표에서 우리가 가장 배우고 싶은 부분입니다")
qs = [("어휘(온톨로지)를 누가 어떻게 관리했나요?", "한 사람 담당으로 정했는데도 동시 편집이 났습니다. assert와 리포트 숫자 말고 방법이 있었나요?"),
      ("LLM 출력의 흔들림을 어떻게 다뤘나요?", "temperature 0도 흔들렸습니다. 평가셋을 두 번 돌리는 것 말고 더 나은 방법이 있을까요?"),
      ("판정을 LLM에 맡긴 팀은 재현성·출처를 어떻게 확보했나요?", "우리는 도구로 넘겼는데, 그 대가로 표현이 딱딱해졌습니다."),
      ("사용자 입력을 어디까지 대화로 받았나요?", "우리는 길어질수록 결과가 흔들려 두 영역만 물었습니다. 더 자연스럽게 받으면서 안정적인 방법이 있었나요?")]
for i, (q, d) in enumerate(qs):
    cy = 1.9 + i * 1.22
    rect(s, 0.6, cy, 12.1, 1.05, T["card"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.85), Inches(cy + 0.27), Inches(0.5), Inches(0.5))
    o.fill.solid(); o.fill.fore_color.rgb = rgb(T["accent"]); o.line.fill.background(); etree.SubElement(o._element.spPr, qn("a:effectLst"))
    tf = o.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = "Q"; r.font.bold = True; r.font.size = Pt(14); r.font.color.rgb = rgb("FFFFFF"); r.font.name = "Arial"
    tb(s, 1.6, cy + 0.15, 10.9, 0.4, q, size=15, bold=True, color=T["text"])
    tb(s, 1.6, cy + 0.55, 10.9, 0.45, d, size=11.5, color=T["muted"])

# ════════════════════════════════════════════════════════════════════
# 17. 역할과 회고
s = prs.slides.add_slide(BLANK)
header(s, 15, "역할과 회고 — 각자 \"가장 크게 틀렸던 것\"", "이름·회고 문장은 팀원이 직접 채웁니다 (초안)")
rows = [["역할", "담당 (이름)", "맡은 것", "가장 크게 틀렸던 것", "다음엔"],
        ["A · 어휘·PM", "(이름)", "vocab.py — 대표 표기 139 · IS_A 102 · 성향↔역량", "(직접 작성)", "(직접 작성)"],
        ["B · 조회·통합", "(이름)", "graph_store.py — 조회 4함수 · 점수식 · Git 통합", "(직접 작성)", "(직접 작성)"],
        ["C · 데이터", "(이름)", "수집 스냅샷 · 추출 배치 · 필터 · 그래프 생성", "(직접 작성)", "(직접 작성)"],
        ["D · 온라인", "(이름)", "app.py 카드·문단 · 인터뷰 · 웹 · 평가셋", "(직접 작성)", "(직접 작성)"]]
table(s, 0.6, 1.9, 12.1, rows, [1.8, 1.4, 3.6, 2.9, 2.4], font_size=11, row_h=0.72, first_col_bold=True)
card(s, 0.6, 5.75, 12.1, 0.95, title=None, body="예시 (이 프로젝트에서 실제로 있었던 것): \"규칙이 지워진 줄 알았는데 diff를 보니 한 단어였다\" · \"설명서만 머지한 줄 알았는데 브랜치 전체였다\" · \"7영역을 다 물으면 더 정확할 줄 알았다\"", body_size=11.5)

# ════════════════════════════════════════════════════════════════════
# 18. 마무리 (dark) — 배운 문장 모음
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, W, H, T["dark"])
node_motif(s, 11.3, 0.5, scale=1.2, colors=["5B6BC4", T["accent"], "5B6BC4"])
tb(s, 0.9, 0.7, 10, 0.7, "배운 문장 여섯 개", size=30, bold=True, color=T["dark_text"])
lessons = ["LLM에게 \"없다\"라고 말할 권리를 주지 않으면, 있는 것처럼 말한다.",
           "온톨로지는 \"A는 B의 한 종류\" 100줄이었다. 방향(위로만)을 지키는 게 전부.",
           "고치기 전에 정답지를 먼저 쓴다. 없으면 \"고쳤다\"와 \"옮겼다\"를 구분할 수 없다.",
           "\"약점을 쓰지 않는다\"는 결정과 \"약점이라는 단어를 지운다\"는 구현은 다른 일이다.",
           "더 많이 물으면 더 잘 아는 게 아니라, 더 많이 흔들렸다.",
           "역할을 나눠도 파일은 겹친다. 문서와 숫자가 없었으면 다투다 끝났을 것이다."]
for i, l in enumerate(lessons):
    y = 1.7 + i * 0.78
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.9), Inches(y + 0.08), Inches(0.42), Inches(0.42))
    o.fill.solid(); o.fill.fore_color.rgb = rgb(T["accent"]); o.line.fill.background(); etree.SubElement(o._element.spPr, qn("a:effectLst"))
    tf = o.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = str(i + 1); r.font.bold = True; r.font.size = Pt(12); r.font.color.rgb = rgb("FFFFFF"); r.font.name = "Arial"
    tb(s, 1.55, y + 0.1, 11.0, 0.5, l, size=16, color=T["dark_text"])
tb(s, 0.9, 6.55, 11.5, 0.5, "감사합니다 — 코드·문서·결정 기록: github.com/KU-CS-HTG/LG-CNS-KG-Project-1 (docs/ 12개 문서, 평가셋 24건)", size=12, color=T["dark_muted"])

# ════════════════════════════════════════════════════════════════════
# 부록 A. 예상 질문
s = prs.slides.add_slide(BLANK)
header(s, None, "부록 A — 예상 질문과 답", "Q&A 대비 (설명서 6-1, 시연 대본, 챗봇 대조 문서에서 취합)")
rows = [["질문", "답"],
        ["왜 어학이 없나? B2B 영업은 외국어가 핵심인데", "역량이 아니라 지원 요건(OPIc IH 이상). 과목명으로 영어를 기르는 전공이 없고, Skill로 세면 어학을 명시한 직무만 불리해진다(신입 85건 중 27건). 정보로 살리려면 카드 표시만"],
        ["왜 서울대만?", "교육과정 데이터가 1개교. 대학 비교 축이 없어 \"서울대 교육과정 기준 전공 추천\"으로 정의"],
        ["CNS 신입 공고가 닫혔는데?", "9/11 스냅샷. 그래서 \"없다\"가 아니라 \"이 스냅샷에 없다\"라고 날짜를 붙여 말한다"],
        ["ChatGPT에 물으면 안 되나?", "결론(통계학과)은 같을 수 있다. 다른 건 근거 — \"46개 중 1위·과목 7개·요구 2개 중 2개\"를 세어서 보여주는 것과 \"1위 후보로 봅니다\"는 다르다"],
        ["LLM은 어디에 쓰나?", "판정이 아니라 추출(과목·공고 → 역량)과 표현(설명 문단). 판정은 사전 조회와 집합 연산"],
        ["ChatGPT는 안 지어내던데? (\"개수를 시키면 지어낸다\"와 충돌?)", "모델·프롬프트에 따라 다르다. 같은 날 ChatGPT 5.6은 비웠고 뤼튼은 채웠다(과목 2/3 없음). 모델 행동에 기대지 않고 데이터로 채운 이유"],
        ["46%는 무슨 뜻?", "\"어울릴 확률\"이 아니라 학생 역량이 그 전공 과목과 이어지는 정도(√idf 가중 커버리지). 1위가 22%인 입력도 있다"]]
table(s, 0.6, 1.85, 12.1, rows, [4.0, 8.1], font_size=10.5, row_h=0.62, first_col_bold=True)

# 부록 B. 수치·문서
s = prs.slides.add_slide(BLANK)
header(s, None, "부록 B — 수치와 문서 지도", "발표 수치 원본과 결정 기록. 전부 저장소 docs/ 에 있다")
rows = [["항목", "값"],
        ["입력", "서울대 105 전공 · 과목 3,829행(고유 3,560) / LG 계열사 9곳 · 공고 50 → 직무 172(신입 85)"],
        ["그래프", "Major 61 · Job 108(신입 75) · Skill 120 · Trait 30 · SoftSkill 10 / DEVELOPS 174(근거 과목 454) · REQUIRES 277 · PREFERS 170 · IS_A 102 · SUGGESTS 7 · MATCHES 17 · WANTS 83"],
        ["어휘", "대표 표기 139 · 별칭 417 · 상위 개념 23 · 공통 Skill 30 · IS_A 한 홉 연결 75"],
        ["LLM 호출", "오프라인 277회(1회성) · 온라인 --basic 2 / --interview 4~6 / 기본 대화 6~8 / --profile 3 · check.py ≈45"],
        ["검증", "확인 3건 · 평가셋 3질문 20/20 · 인터뷰 4/4 (두 번 연속)"]]
table(s, 0.6, 1.85, 12.1, rows, [1.8, 10.3], font_size=10.5, row_h=0.6, first_col_bold=True)
docs = ["09-15 전공추출_필터수정 · 온톨로지_계층", "09-16 어휘_3단계_초안 · 대화형_입력_검토 · render_v2_스펙 · 인터뷰_평가_회귀_분석 · 발표_수치_4-5장 · 시연_대본",
        "09-17 발표_내용_취합 · 챗봇_대조 · 쉽게-읽는-프로젝트-소개 · 프로젝트-설명서(12장, 1,200줄)"]
card(s, 0.6, 5.1, 12.1, 1.55, title="결정 기록 (docs/, 날짜순)", body=docs, body_size=11, icon="D")

out = sys.argv[2] if len(sys.argv) > 2 else f"deck_{THEME}.pptx"
prs.save(out); print("saved", out, len(prs.slides), "slides")
