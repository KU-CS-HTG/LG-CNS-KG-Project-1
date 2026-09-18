"""발표 초안 6장(AI & Agent 워크플로우, 사용 기술) 대체안 — 글머리 12줄 대신 '어디에 AI가 있고 어디가 코드인가'를 그림으로.
kg_slides.py 의 헬퍼(header/card/rect/tb/motif)를 그대로 쓴다. 사용: slide6.py out.pptx
"""
import sys, pathlib
src = pathlib.Path(__file__).with_name("kg_slides.py").read_text(encoding="utf-8")
exec(src.split("# ── 데이터")[0])          # 헬퍼·색·prs 정의까지만 실행

AI, CODE, DICT = CORAL_MARK, "2F6FD6", GREEN_MARK   # AI 배지 · 코드 배지 · 사전
AI_BG, CODE_BG, DICT_BG = "FDECEA", "E8EFFB", "E6F5EC"


def badge(s, x, y, text, color, w=0.62):
    o = rect(s, x, y, w, 0.24, color, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    tf = o.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = text
    r.font.size = Pt(9); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = rgb("FFFFFF")


def step(s, x, y, w, h, title, sub, who):
    fill = {"AI": AI_BG, "코드": CODE_BG, None: CARD}[who]
    rect(s, x, y, w, h, fill, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08, line=LINE)
    tb(s, x + 0.1, y + 0.42, w - 0.2, 0.3, title, 12.5, True, TITLE, align=PP_ALIGN.CENTER)
    tb(s, x + 0.1, y + 0.74, w - 0.2, 0.5, sub, 9.5, False, MUTED, align=PP_ALIGN.CENTER)
    if who: badge(s, x + (w - 0.62) / 2, y + 0.12, who, AI if who == "AI" else CODE)


def harrow(s, x1, x2, y):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y), Inches(x2), Inches(y))
    c.line.color.rgb = rgb(GRAY); c.line.width = Pt(1.5)
    ln = c.line._get_or_add_ln(); t = etree.SubElement(ln, qn("a:tailEnd")); t.set("type", "triangle"); t.set("w", "med"); t.set("len", "med")


def card2(s, x, y, w, h, who, color, title):
    rect(s, x, y, w, h, CARD, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.04, line=LINE)
    badge(s, x + 0.25, y + 0.21, who, color)
    tb(s, x + 0.97, y + 0.18, w - 1.2, 0.3, title, 13, True, TITLE)


def bullets(s, x, y, w, items, size=10.5, gap=0.3):
    paras = []
    for it in items:
        runs = it if isinstance(it, list) else [(it, {})]
        paras.append([("•  ", {"color": MUTED})] + runs)
    t = tb(s, x, y, w, gap * len(items), paras, size, False, TEXT)
    for p in t.text_frame.paragraphs: p.space_after = Pt(5)
    return t


s = prs.slides.add_slide(BLANK)
header(s, "05", "AI & Agent 워크플로우, 사용 기술", "AI는 두 곳(말 → 태그, 카드 → 말)에만 — 판정 세 곳은 코드가 세고, 둘을 잇는 것이 사전")

# ── 위: 한 줄 흐름 (배지로 AI/코드 구분) ─────────────────────────────
steps = [("학생 이야기", "자기소개 · 질문 답", None), ("역량 태그", "말 → 사전에 있는 단어만", "AI"),
         ("전공 순위", "61개 전부 비교", "코드"), ("직무 · 과목", "충족/부족 세기 · 다리 과목 3개", "코드"), ("카드 + 설명", "숫자는 카드, 말은 AI", "AI")]
sw, sg, sy, sh = 2.25, 0.27, 1.9, 1.3
for i, (t1, t2, who) in enumerate(steps):
    x = 0.5 + i * (sw + sg)
    step(s, x, sy, sw, sh, t1, t2, who)
    if i < len(steps) - 1: harrow(s, x + sw + 0.03, x + sw + sg - 0.03, sy + sh / 2)
# 코드 두 칸 아래 띠
bx1 = 0.5 + 2 * (sw + sg); bx2 = 0.5 + 4 * (sw + sg) - sg
rect(s, bx1, sy + sh + 0.1, bx2 - bx1, 0.3, CODE_BG, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
tb(s, bx1, sy + sh + 0.1, bx2 - bx1, 0.3, "graph.json 조회 — 딕셔너리 · 집합 연산 · LLM 0회 · 같은 태그면 항상 같은 답", 10, True, CODE, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# ── 아래: 카드 3개 ────────────────────────────────────────────────
cy, ch_, cw3, cg = 3.6, 2.85, 3.95, 0.24
# ① AI 2곳
x = 0.5; card2(s, x, cy, cw3, ch_, "AI", AI, "AI 2곳 — 어떻게 묶어 두나")
bullets(s, x + 0.25, cy + 0.6, cw3 - 0.5, [
    [("형식은 스키마가 강제", {"bold": True}), (" — Pydantic 으로 틀을 정함", {})],
    [("사전에 없는 단어는 버림", {"bold": True}), (" — 지어낸 역량 차단", {})],
    [("무작위성 끔", {"bold": True}), (" — temperature 0", {})]])
rect(s, x + 0.25, cy + 1.8, cw3 - 0.5, 0.82, BG, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
tb(s, x + 0.38, cy + 1.88, cw3 - 0.76, 0.7, [[("예)  ", {"bold": True, "color": MUTED}), ("\"통계 수업이 재밌고 파이썬으로 데이터 정리\"", {"color": TEXT})],
                                             [("→  ", {"color": MUTED}), ("Statistics · Python · Data Analysis", {"bold": True, "color": AI})]], 10)
# ② 코드 3곳
x = 0.5 + cw3 + cg; card2(s, x, cy, cw3, ch_, "코드", CODE, "코드 3곳 — 무엇을 세나")
bullets(s, x + 0.25, cy + 0.6, cw3 - 0.5, [
    [("전공 순위", {"bold": True}), (" — 61개 전부 비교해 순위 · %", {})],
    [("직무 매칭", {"bold": True}), (" — 신입 75개, 요구 역량 충족/부족", {})],
    [("과목 3개", {"bold": True}), (" — 전공과 직무를 잇는 다리", {})]])
rect(s, x + 0.25, cy + 1.8, cw3 - 0.5, 0.82, BG, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
tb(s, x + 0.38, cy + 1.88, cw3 - 0.76, 0.7, [[("예)  ", {"bold": True, "color": MUTED}), ("통계학과 46% (61개 중 1위)", {"bold": True, "color": CODE})],
                                             [("→  ", {"color": MUTED}), ("소재개발AX 요구 역량 2/2 충족 · 다리 과목 3개", {"color": TEXT})]], 10)
# ③ 사전
x = 0.5 + 2 * (cw3 + cg); card2(s, x, cy, cw3, ch_, "사전", DICT, "둘을 잇는 사전 — 그래프의 본체")
bullets(s, x + 0.25, cy + 0.6, cw3 - 0.5, [
    [("이름 139개", {"bold": True}), (" — 표기가 달라도 같은 역량은 한 이름", {})],
    [("상하 관계 102개", {"bold": True}), (" — \"Oracle은 Database의 한 종류\"", {})],
    [("한 단계, 위로만", {"bold": True}), (" — 도구 이름 → 학문 이름", {})]])
# 미니 그래프: 전공 → 역량 ← 직무, 아래 하위 역량
gx, gy = x + 0.55, cy + 2.15
motif(s, gx, gy, 0.16, 0.55)
tb(s, gx - 0.3, gy + 0.12, 0.6, 0.2, "전공", 8, False, MUTED, align=PP_ALIGN.CENTER)
tb(s, gx + 0.55 - 0.3, gy - 0.3, 0.6, 0.2, "역량", 8, False, MUTED, align=PP_ALIGN.CENTER)
tb(s, gx + 1.1 - 0.3, gy + 0.12, 0.6, 0.2, "직무", 8, False, MUTED, align=PP_ALIGN.CENTER)
tb(s, gx + 0.55 + 0.12, gy + 0.55 * 0.8 - 0.1, 1.2, 0.2, "하위 역량 (IS_A)", 8, False, MUTED)
tb(s, x + 2.15, cy + 2.05, 1.7, 0.6, [[("전공 61 · 역량 120 · 직무 108", {"bold": True, "color": TITLE})], [("graph.json — Python dict, Neo4j 없이", {"color": MUTED})]], 9.5)

# ── 맨 아래: 기술 한 줄 ──────────────────────────────────────────
tb(s, 0.5, 6.62, 12.3, 0.3, [[("쓴 것  ", {"bold": True, "color": TITLE}), ("OpenAI gpt-4o-mini · LangChain (프롬프트 | 모델 | 스키마) · Pydantic · Flask + SSE(설명 문단 흘려보내기) · graph.json + Python dict · 평가셋 24건 자동 채점", {"color": MUTED})]], 10.5)
s.notes_slide.notes_text_frame.text = ("위 흐름에서 빨간 배지 두 곳만 AI. 가운데 파란 두 칸은 graph.json 을 읽는 코드라 같은 태그면 항상 같은 답. "
                                       "AI 를 묶는 방법 셋(스키마·사전·temperature 0), 코드가 세는 것 셋(전공 순위·직무 충족/부족·다리 과목), 둘을 잇는 사전(이름 139 + 상하 102). "
                                       "기술 이름은 맨 아래 한 줄 — 질문 오면 부록으로.")

out = sys.argv[1] if len(sys.argv) > 1 else "slide6.pptx"
prs.save(out); print("saved", out)
