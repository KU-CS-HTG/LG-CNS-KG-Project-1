"""발표 초안 3장(Overall Architecture) 대체안 — 5장(서비스 구조)과 합친 한 장.
지도 만들기(오프라인) / 지도 읽기(온라인) 두 띠 + 각 상자에 파일명 + AI 배지. 선은 가로·세로만, 색은 AI/코드/사전 셋만.
사용: slide3.py out.pptx
"""
import sys, pathlib
src = pathlib.Path(__file__).with_name("kg_slides.py").read_text(encoding="utf-8")
exec(src.split("# ── 데이터")[0])

AI, CODE, DICT = CORAL_MARK, "2F6FD6", GREEN_MARK
AI_BG, CODE_BG, DICT_BG, DATA_BG = "FDECEA", "E8EFFB", "E6F5EC", "FFFFFF"


def badge(s, x, y, text, color, w=0.5):
    o = rect(s, x, y, w, 0.22, color, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    tf = o.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = text
    r.font.size = Pt(8.5); r.font.bold = True; r.font.name = FONT; r.font.color.rgb = rgb("FFFFFF")


def box(s, x, y, w, h, title, sub, file, who=None):
    fill = {"AI": AI_BG, "코드": CODE_BG, "사전": DICT_BG, None: DATA_BG}[who]
    rect(s, x, y, w, h, fill, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08, line=LINE)
    tb(s, x + 0.1, y + 0.14, w - 0.2, 0.3, title, 12, True, TITLE, align=PP_ALIGN.CENTER)
    tb(s, x + 0.1, y + 0.44, w - 0.2, 0.3, sub, 9.5, False, MUTED, align=PP_ALIGN.CENTER)
    if file: tb(s, x + 0.1, y + h - 0.32, w - 0.2, 0.25, file, 8.5, False, {"AI": AI, "코드": CODE, "사전": DICT, None: GRAY}[who], align=PP_ALIGN.CENTER)
    if who: badge(s, x + w - 0.6, y + 0.1, who, {"AI": AI, "코드": CODE, "사전": DICT}[who])


def arrow(s, x1, y1, x2, y2, color=GRAY, w=1.5):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color); c.line.width = Pt(w)
    ln = c.line._get_or_add_ln(); t = etree.SubElement(ln, qn("a:tailEnd")); t.set("type", "triangle"); t.set("w", "med"); t.set("len", "med")


def band(s, x, y, w, h, label, sub, fill="F9FAFD"):
    rect(s, x, y, w, h, fill, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.03, line=LINE)
    tb(s, x + 0.25, y + 0.12, 6, 0.3, [[(label, {"bold": True, "size": 12, "color": TITLE}), ("   " + sub, {"size": 10, "color": MUTED})]], 12)


s = prs.slides.add_slide(BLANK)
header(s, "02", "Overall Architecture — 지도를 한 번 만들고, 매번 읽는다", "위: 미리 한 번 만드는 지도(오프라인)  ·  아래: 학생이 올 때마다 도는 순서(온라인)  ·  빨간 배지 = AI, 파란 배지 = 코드")

# ── ① 지도 만들기 (오프라인) ─────────────────────────────────────
band(s, 0.5, 1.85, 12.33, 2.2, "① 지도 만들기 — 오프라인", "갱신할 때 한 번 · LLM 277회 · 결과는 파일로 캐시")
by, bh = 2.35, 1.35
def small_box(s, x, y, w, h, title, sub, file):
    rect(s, x, y, w, h, DATA_BG, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08, line=LINE)
    tb(s, x + 0.1, y + 0.07, w - 0.2, 0.26, title, 11.5, True, TITLE, align=PP_ALIGN.CENTER)
    tb(s, x + 0.1, y + 0.32, w - 0.2, 0.22, sub, 9, False, MUTED, align=PP_ALIGN.CENTER)
    tb(s, x + 0.1, y + 0.52, w - 0.2, 0.2, file, 8, False, GRAY, align=PP_ALIGN.CENTER)


small_box(s, 0.75, 2.28, 2.2, 0.75, "서울대 교육과정", "105개 전공 · 3,829과목", "대학알리미 → subject_cleaned.csv")
small_box(s, 0.75, 3.1, 2.2, 0.75, "LG 채용 공고", "9개 계열사 · 172개 직무", "lg_careers.py → data/raw 스냅샷")
arrow(s, 2.98, 2.65, 3.42, 2.65); arrow(s, 2.98, 3.47, 3.42, 3.47)
box(s, 3.45, by, 2.75, bh, "역량 이름 뽑기", "과목명·공고 문장 → 역량 태그 (캐시)", "build_graph_majors.py · transform_v2.py", "AI")
arrow(s, 6.23, 3.02, 6.67, 3.02)
box(s, 6.7, by, 2.75, bh, "사전으로 이름 통일", "이름 139개 · 상하 관계 102개", "vocab.py", "사전")
arrow(s, 9.48, 3.02, 9.92, 3.02)
box(s, 9.95, by, 2.6, bh, "지도 완성", "전공 61 — 역량 120 — 직무 108", "build_graph_jobs.py → data/graph.json", "코드")

# 지도 → 온라인 판정 칸으로 (세로 점선)
gx = 10.25
c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(gx), Inches(3.72), Inches(gx), Inches(4.78))
c.line.color.rgb = rgb(CODE); c.line.width = Pt(1.5); ln = c.line._get_or_add_ln(); ln.insert(0, etree.Element(qn("a:prstDash"), val="dash"))
tb(s, gx + 0.1, 4.08, 1.6, 0.25, "이 지도를 읽는다 ↓", 9, True, CODE)

# ── ② 지도 읽기 (온라인) ─────────────────────────────────────────
band(s, 0.5, 4.3, 12.33, 2.35, "② 지도 읽기 — 온라인", "학생 1명당 LLM 2~6회 · 판정은 LLM 0회")
oy, oh, ow, og = 4.8, 1.35, 2.2, 0.28
ox = [0.75 + i * (ow + og) for i in range(5)]
box(s, ox[0], oy, ow, oh, "학생 이야기", "웹 채팅 · 6영역 적응형 질문", "webapp.py · interview.py", None)
box(s, ox[1], oy, ow, oh, "역량 태그", "말 → 사전에 있는 단어만", "app.py + user_analysis/", "AI")
box(s, ox[2], oy, ow, oh, "전공 순위", "61개 전부 비교 → 1위", "graph_store.py", "코드")
box(s, ox[3], oy, ow, oh, "직무 · 과목", "충족/부족 세기 · 다리 과목 3개", "graph_store.py", "코드")
box(s, ox[4], oy, ow, oh, "카드 + 설명", "숫자는 카드 · 말은 AI (SSE)", "app.py render / explain", "AI")
for i in range(4): arrow(s, ox[i] + ow + 0.03, oy + oh / 2, ox[i + 1] - 0.03, oy + oh / 2)
# 태그 실패 시 되묻기 — 아래로 돌아가는 세 토막 (마지막에만 화살촉)
lx1, lx0, ly = ox[1] + ow / 2, ox[0] + ow / 2, oy + oh + 0.22
for (a, b, c2, d), head in (((lx1, oy + oh + 0.02, lx1, ly), False), ((lx1, ly, lx0, ly), False), ((lx0, ly, lx0, oy + oh + 0.02), True)):
    cn = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(a), Inches(b), Inches(c2), Inches(d))
    cn.line.color.rgb = rgb(GRAY); cn.line.width = Pt(1)
    if head:
        ln = cn.line._get_or_add_ln(); t = etree.SubElement(ln, qn("a:tailEnd")); t.set("type", "triangle"); t.set("w", "sm"); t.set("len", "sm")
tb(s, (lx0 + lx1) / 2 - 0.7, ly + 0.03, 1.4, 0.22, "태그 실패 시 되묻기", 8.5, False, MUTED, align=PP_ALIGN.CENTER)

tb(s, 0.5, 6.78, 12.3, 0.28, [[("그래프 = ", {"bold": True, "color": TITLE}), ("graph.json 파일 하나 + Python dict (Neo4j 없이)  ·  ", {"color": MUTED}),
                               ("웹 = ", {"bold": True, "color": TITLE}), ("Flask, /api/interview/answer · /api/explain (SSE)  ·  ", {"color": MUTED}),
                               ("검사 = ", {"bold": True, "color": TITLE}), ("check.py, 평가셋 24건", {"color": MUTED})]], 10)
s.notes_slide.notes_text_frame.text = ("위 띠: 지도 만들기. 과목 3,829개와 공고 172개에서 AI가 역량 이름을 뽑고(277회, 캐시), 사전으로 이름을 통일해 graph.json 하나로 만든다. "
                                       "아래 띠: 학생이 올 때마다. AI는 맨 앞(말→태그)과 맨 뒤(카드→말) 두 곳뿐, 가운데 전공 순위·직무·과목은 graph_store.py 가 지도를 읽어서 센다. "
                                       "파일 이름은 상자 아래 작은 글씨 — 질문 오면 그걸로 답한다.")

out = sys.argv[1] if len(sys.argv) > 1 else "slide3.pptx"
prs.save(out); print("saved", out)
