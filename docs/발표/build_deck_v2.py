# -*- coding: utf-8 -*-
"""발표 PPT 초안 v2 — Graph Ink 테마. v1 대비: 쉬운 말로 순화, 글자 줄임, 이미지(흐름도·'한 종류' 관계·챗봇 대화 카드) 사용."""
import sys, os
from deck_lib import *   # prs, T, W, H, BLANK, rect, tb, bullets, node_motif, header, card, lesson, table, mono, callout
from pptx.util import Inches, Pt

IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "img")


def pic(slide, name, x, y, w=None, h=None):
    path = os.path.join(IMG, name)
    kw = {}
    if w: kw["width"] = Inches(w)
    if h: kw["height"] = Inches(h)
    return slide.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def pic_fit(slide, name, x, y, box_w, box_h):
    """box 안에 비율 유지로 맞추고 가로 가운데 정렬."""
    from PIL import Image
    iw, ih = Image.open(os.path.join(IMG, name)).size
    scale = min(box_w / iw, box_h / ih)
    w, h = iw * scale, ih * scale
    return slide.shapes.add_picture(os.path.join(IMG, name), Inches(x + (box_w - w) / 2), Inches(y), width=Inches(w), height=Inches(h))


def trial(num, title, sub, cols, lesson_text, notes=None):
    s = prs.slides.add_slide(BLANK)
    header(s, num, title, sub)
    labels = ["무슨 일이", "왜", "어떻게 알아챘나", "어떻게 바꿨나"]
    icons = ["!", "?", "◉", "→"]
    colors = [T["accent"], T["accent"], T["primary"], T["good"]]
    cw, gap, x0, y0 = 2.85, 0.23, 0.6, 1.85
    for i, (lab, body) in enumerate(zip(labels, cols)):
        card(s, x0 + i * (cw + gap), y0, cw, 3.85, title=lab, body=body, title_color=colors[i], body_size=12.5, icon=icons[i])
    lesson(s, lesson_text, y=6.0)
    s.notes_slide.notes_text_frame.text = notes or f"[{title}] 무슨 일이 → 왜 → 어떻게 알아챘나 → 어떻게 바꿨나. 마지막에 배운 문장을 그대로 읽는다: {lesson_text}"
    return s


# 1. 표지 ─────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, W, H, T["dark"])
node_motif(s, 9.6, 1.1, scale=2.6, colors=["5B6BC4", T["accent"], "5B6BC4"])
tb(s, 0.9, 1.5, 8.6, 0.5, "LG CNS AI캠퍼스 · Knowledge Graph 과정 · 3주차 미니 프로젝트", size=14, color=T["dark_muted"])
tb(s, 0.9, 2.1, 9.2, 1.9, [[("역량 경로 추천", {"size": 44, "bold": True, "color": T["dark_text"]})],
                           [("내 관심사 → 전공 → 과목 → LG 신입 직무를 데이터로 잇는 지도", {"size": 22, "color": T["dark_text"]})]], size=22)
tb(s, 0.9, 4.15, 9.5, 0.8, [[("\"좋아하는 것\"에서 \"첫 직장\"까지 — ", {"size": 18, "color": T["dark_muted"]}),
                            ("지어내지 않고 데이터로", {"size": 18, "bold": True, "color": T["accent"]})]], size=18)
tb(s, 0.9, 5.6, 9.5, 0.9, [[("무엇을 만들었나보다 ", {"size": 14, "color": T["dark_muted"]}), ("무엇이 틀렸고, 어떻게 알아챘고, 무엇을 배웠나", {"size": 14, "bold": True, "color": T["dark_text"]})],
                           [("팀 4명 · 2026-09-14 ~ 09-18 · 서울대 교육과정 × LG 채용 공고", {"size": 12, "color": T["dark_muted"]})]], size=14)
s.notes_slide.notes_text_frame.text = "이 발표는 결과 자랑이 아니라, 나흘 동안 무엇이 틀렸고 어떻게 알아챘는지에 대한 이야기입니다."

# 2. 구성 ─────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, None, "오늘 이야기 — 성과 두 장, 틀렸던 이야기 여섯 장", "여섯 장 모두 같은 순서로: 무슨 일이 → 왜 → 어떻게 알아챘나 → 어떻게 바꿨나 → 배운 문장 한 줄")
items = [("AI는 시키면 채운다", "첫 시도에서 102개 전공 중 22개만 잡힘"), ("글자가 같아야 이어진다", "전공과 직무가 서로 다른 말을 쓰고 있었다"),
         ("눈 대신 정답지", "점수 계산을 세 번 바꿨고, 매번 정답지가 잡았다"), ("한 단어의 무게", "\"명확하게\" 한 단어에 결과가 흔들렸다"),
         ("대화는 입력만", "더 많이 물으면 더 많이 흔들렸다"), ("넷이 한 파일을 고치면", "같은 파일을 동시에 고쳐 세 번 부딪혔다")]
for i, (t1, t2) in enumerate(items):
    cx = 0.6 + (i % 3) * 4.1; cy = 2.0 + (i // 3) * 2.0
    card(s, cx, cy, 3.85, 1.7, title=t1, body=t2, body_size=12.5, title_size=16, icon=str(i + 1))
tb(s, 0.6, 6.25, 12, 0.4, "앞뒤로: 무엇을 만들었나(30초 데모) · 챗봇에게 같은 질문을 해 보니 · 한계 · 다른 팀에 묻고 싶은 것", size=12, color=T["muted"])

# 3. 무엇을 만들었나 ───────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 1, "무엇을 만들었나", "고등학생이 \"이런 걸 좋아해요\"라고 말하면 → \"이 전공, 이 과목, 그리고 LG의 이 일\"을 근거와 함께 답한다")
steps = [("학생 이야기", "자기소개나\n질문 3개", T["muted"]), ("역량 태그", "사전에 있는 단어로\n예) 데이터 분석", T["primary"]),
         ("전공 1위", "전공 61개 전부 비교\n예) 통계학과", T["primary"]), ("직무", "전공이 기르는 역량으로\n예) LG에너지솔루션", T["primary"]),
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
card(s, 0.6, 4.4, 5.9, 1.75, title="답은 \"지도\" 위에서만 찾는다", body="실제 교육과정과 실제 채용 공고를 모아 전공–역량–직무를 선으로 이어 둔 지도. 카드에 나오는 전공·과목·직무 이름은 전부 이 지도에 실제로 있는 것", body_size=12.5, icon="=")
card(s, 6.8, 4.4, 5.9, 1.75, title="AI는 두 군데에만", body="① 글에서 역량 이름 뽑기  ② 카드를 친절한 말로 풀어 쓰기. 어떤 전공·직무를 고를지(판정)는 AI가 아니라 계산이 한다 — 그래서 같은 이야기에 같은 답", body_size=12.5, icon="AI")

# 4. 30초 데모 ───────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 2, "30초 데모 — 학생이 보는 카드", "입력: \"데이터 분석이 재미있어요 / 통계 수업, 파이썬으로 데이터 정리\"  (실제 출력)")
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
출처 · 과목: 서울대학교 교육과정 — 대학알리미 · 공고: LG Careers"""
mono(s, 0.6, 1.8, 7.9, 5.15, card_text, size=10)
callout(s, 8.8, 2.35, 4.0, "① 61개 전공을 전부 비교했다")
tb(s, 8.8, 2.82, 4.0, 0.6, "떠오른 서너 개 중에 고르는 챗봇과 다른 첫 줄", size=11.5, color=T["muted"])
callout(s, 8.8, 3.45, 4.0, "② 이어진 것 ✓ · 안 이어진 것 ○", color=T["good"])
tb(s, 8.8, 3.92, 4.0, 0.7, "안 이어진 역량(Python)도 숨기지 않는다. 46%는 \"어울릴 확률\"이 아니라 역량이 이어진 정도", size=11.5, color=T["muted"])
callout(s, 8.8, 4.75, 4.0, "③ 전부 실제로 있는 과목·직무", color=T["primary"])
tb(s, 8.8, 5.22, 4.0, 0.9, "3,829개 과목·172개 직무 데이터에 있는 이름만 나온다 — 매번 자동 확인. 이 아래에 AI가 쓴 설명 문단이 붙는다", size=11.5, color=T["muted"])

# 5. 재료 ─────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 3, "재료 — 숫자 여덟 개", "지어내지 않으려면 진짜 재료가 있어야 한다")
stats = [("105", "서울대 전공", "과목 3,829개 (대학알리미)"), ("9곳", "LG 계열사", "공고 50건 → 직무 172개 (신입 85)"),
         ("61·120·108", "전공 · 역량 · 직무", "지도의 점 세 종류"), ("139", "사전의 단어", "같은 뜻은 한 단어로"),
         ("277번", "지도 만들 때 AI 호출", "한 번만, 결과는 저장"), ("2~6번", "학생 1명당 AI 호출", "판정에는 0번"),
         ("24 / 24", "정답지 통과", "고칠 때마다 자동 채점"), ("3가지", "매번 확인하는 것", "같은 답 · 실제 이름 · 개수가 맞나")]
for i, (big, lab, sub) in enumerate(stats):
    cx = 0.6 + (i % 4) * 3.1; cy = 1.95 + (i // 4) * 2.35
    rect(s, cx, cy, 2.85, 2.1, T["card"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06)
    tb(s, cx + 0.2, cy + 0.25, 2.5, 0.8, big, size=24 if len(big) > 8 else 36, bold=True, color=T["primary"], font="Arial")
    tb(s, cx + 0.2, cy + 1.1, 2.5, 0.4, lab, size=13, bold=True, color=T["text"])
    tb(s, cx + 0.2, cy + 1.48, 2.5, 0.55, sub, size=11, color=T["muted"])

# 6. 어떻게 동작하나 — 도형·글자 (편집 가능) ───────────────────────
def flow_box(slide, x, y, w, h, title, sub, fill, tcol, sub_size=10.5):
    rect(slide, x, y, w, h, fill, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.1)
    tb(slide, x + 0.1, y + 0.14, w - 0.2, 0.38, title, size=13, bold=True, color=tcol, align=PP_ALIGN.CENTER)
    tb(slide, x + 0.1, y + 0.52, w - 0.2, h - 0.6, sub, size=sub_size, color=T["muted"], align=PP_ALIGN.CENTER)


def harrow(slide, x1, x2, y, dashed=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y), Inches(x2), Inches(y))
    c.line.color.rgb = rgb(T["muted"]); c.line.width = Pt(2)
    ln = c.line._get_or_add_ln(); tail = etree.SubElement(ln, qn("a:tailEnd")); tail.set("type", "triangle"); tail.set("w", "med"); tail.set("len", "med")
    if dashed: ln.insert(0, etree.Element(qn("a:prstDash"), val="dash"))
    return c


s = prs.slides.add_slide(BLANK)
header(s, 4, "어떻게 동작하나 — 지도를 한 번 만들고, 매번 읽는다")
CARD2 = T["card2"]; DONE = "DFE8F4"
# ── ① 지도 만들기
tb(s, 0.6, 1.5, 11, 0.35, [[("① 지도 만들기 — 미리, 한 번만", {"bold": True, "size": 14, "color": T["primary"]}), ("   AI가 글을 읽어 역량 이름을 뽑는다 (총 277번, 결과는 저장)", {"size": 10.5, "color": T["muted"]})]], size=14)
flow_box(s, 0.6, 1.95, 2.2, 0.72, "과목 이름 3,829개", "서울대 105개 전공", T["card"], T["text"], sub_size=10)
flow_box(s, 0.6, 2.8, 2.2, 0.72, "채용 공고 172개", "LG 계열사 9곳", T["card"], T["text"], sub_size=10)
harrow(s, 2.85, 3.3, 2.31); harrow(s, 2.85, 3.3, 3.16)
flow_box(s, 3.35, 2.0, 2.75, 1.5, "AI가 역량 이름 뽑기", "\"통계학과는 통계를 기른다\"\n\"이 직무는 머신러닝을 요구한다\"", CARD2, T["primary"])
harrow(s, 6.15, 6.5, 2.75)
flow_box(s, 6.55, 2.0, 2.75, 1.5, "사전으로 이름 통일", "같은 뜻은 한 단어로 — 139개\n\"Oracle은 Database의 한 종류\" 102개", CARD2, T["primary"], sub_size=10)
harrow(s, 9.35, 9.7, 2.75)
flow_box(s, 9.75, 2.0, 2.95, 1.5, "지도 완성", "전공 61 — 역량 120 — 직무 108\n관계 5종", DONE, T["primary"])
# ── ② 지도 읽기
tb(s, 0.6, 3.85, 8, 0.35, [[("② 지도 읽기 — 학생이 올 때마다", {"bold": True, "size": 14, "color": T["primary"]}), ("   전공·직무·과목은 위 지도에서 찾는다 — AI는 맨 앞과 맨 뒤에만", {"size": 10.5, "color": T["muted"]})]], size=14)
steps = [("학생 이야기", "자기소개나\n질문 3개", T["card"], T["text"]), ("역량 태그", "AI 1번 —\n사전에 있는 단어만", CARD2, T["primary"]),
         ("전공 1위", "61개 전부 비교\n예) 통계학과", CARD2, T["primary"]), ("직무", "전공이 기르는 역량으로\n충족/부족 세기", CARD2, T["primary"]),
         ("과목 3개", "전공과 직무를\n잇는 다리", CARD2, T["primary"]), ("카드 + 설명", "숫자·근거는 카드\n말은 AI 1번", DONE, T["primary"])]
bw, gap, y2 = 1.85, 0.2, 4.3
for i, (t1, t2, fill, col) in enumerate(steps):
    x = 0.6 + i * (bw + gap)
    flow_box(s, x, y2, bw, 1.3, t1, t2, fill, col, sub_size=10)
    if i < len(steps) - 1:
        harrow(s, x + bw + 0.02, x + bw + gap - 0.02, y2 + 0.65)
# 지도 → 판정 세 칸: 점선 + 띠
x1 = 0.6 + 2 * (bw + gap); x2 = 0.6 + 5 * (bw + gap) - gap
rect(s, x1 - 0.08, 5.75, x2 - x1 + 0.16, 0.62, "E6F7EF", MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.3)
tb(s, x1, 5.77, x2 - x1, 0.58, [[("↑ 위에서 만든 지도를 여기서 읽는다", {"bold": True, "size": 12, "color": T["good"]})],
                                 [("전공·직무·과목은 AI가 고르지 않고, 지도에서 찾는다", {"size": 10, "color": T["good"]})]],
   size=12, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
# 지도 완성 → (오른쪽 여백을 돌아) 초록 띠: 점선 3토막, 마지막에 화살촉
pts = [(12.7, 2.75), (12.95, 2.75), (12.95, 6.05), (x2 + 0.1, 6.05)]
for (ax, ay), (bx, by) in zip(pts, pts[1:]):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(ax), Inches(ay), Inches(bx), Inches(by))
    c.line.color.rgb = rgb(T["good"]); c.line.width = Pt(2)
    ln = c.line._get_or_add_ln(); ln.insert(0, etree.Element(qn("a:prstDash"), val="dash"))
    if (bx, by) == pts[-1]:
        tail = etree.SubElement(ln, qn("a:tailEnd")); tail.set("type", "triangle"); tail.set("w", "med"); tail.set("len", "med")
tb(s, 9.75, 3.52, 2.95, 0.3, "이 지도를 읽어서 →", size=10, color=T["good"], bold=True, align=PP_ALIGN.RIGHT)
tb(s, 0.6, 6.6, 12.1, 0.4, "같은 이야기를 두 번 넣으면 같은 답이 나오고, 카드에 나오는 전공·과목·직무 이름은 전부 실제 데이터에 있는 것", size=11.5, color=T["text"])
s.notes_slide.notes_text_frame.text = "위: 지도 만들기(한 번, AI 277번). 아래: 학생이 올 때마다 읽기. 초록 띠 — 전공·직무·과목을 고르는 세 칸은 위에서 만든 지도를 읽을 뿐 AI가 고르지 않는다."

# 6-3. 기술 스택 ─────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 5, "무엇으로 만들었나 — 작게, 표준으로", "Python 약 3,100줄 · 파일 7개 · 외부 라이브러리 5개. 판정을 계산에 맡기려면 도구가 단순해야 했다")
stack = [
    ("언어 · 협업", "Py", [[("Python", {"bold": True}), (" — 코드 3,100줄(팀 모듈 포함 4,500), 파일 7개", {})],
                          [("Git · GitHub", {"bold": True}), (" — 커밋 167 · PR 15 · 기능별 가지에서 작업 후 합치기", {})],
                          [("VS Code · Claude Code", {"bold": True}), (" — 코딩 보조 (동시 편집 사고의 원인이자, 문서화의 도구)", {})]]),
    ("AI", "AI", [[("OpenAI gpt-4o-mini", {"bold": True}), (" — 역량 뽑기·설명 문단 전부 같은 모델, 무작위성 끔", {})],
                  [("LangChain", {"bold": True}), (" — 프롬프트 틀 · 정해진 형식으로 답 받기 · 글자 흘려보내기", {})],
                  [("pydantic", {"bold": True}), (" — AI 답의 형식을 미리 정해 두는 틀(스키마)", {})]]),
    ("데이터 · 수집", "DB", [[("requests", {"bold": True}), (" — LG Careers 내부 API에서 공고 받기, 날짜별로 저장", {})],
                            [("pandas", {"bold": True}), (" — 과목표(3,829행)를 전공 단위로 묶기", {})],
                            [("JSON 파일 3층", {"bold": True}), (" — AI 원답 저장 → 걸러낸 것 → 지도. 별도 DB 없음", {})]]),
    ("지식그래프", "KG", [[("graph.json + Python 사전/집합", {"bold": True}), (" — 점 5종·관계 5종, 겹치는 것 세기로 판정 (AI 0번)", {})],
                        [("vocab.py", {"bold": True}), (" — 공통 사전 139 · '한 종류' 102 · 성향↔역량 (사람이 관리)", {})],
                        [("일부러 뺀 것: Neo4j · 벡터 임베딩", {"bold": True, "color": T["accent"]}), (" — 점 300개 규모라 사전으로 충분. 나중에 옮길 수 있게 설계", {})]]),
    ("화면", "UI", [[("명령줄(CLI)", {"bold": True}), (" — 입력 4방식 + 역방향 질문(--job)", {})],
                   [("Flask 웹", {"bold": True}), (" — 채팅 화면 · 결과 카드 · 설명 문단. 판정은 여기서 하지 않는다", {})],
                   [("실시간 스트리밍", {"bold": True}), (" — 카드는 즉시, 설명 문단은 글자가 흘러나오게", {})]]),
    ("검증 · 문서", "QA", [[("check.py", {"bold": True}), (" — 확인 3가지 + 정답지 24개 자동 채점 (대화도 대본으로 자동)", {})],
                          [("tiktoken", {"bold": True}), (" — AI가 읽는 양(토큰) 실측. 감으로 말하지 않기 위해", {})],
                          [("Markdown + Mermaid", {"bold": True}), (" — 설명서 1,200줄 · 결정 기록 12개 · 시연 대본 · 챗봇 대조", {})]]),
]
for i, (t1, ic, body) in enumerate(stack):
    cx = 0.6 + (i % 3) * 4.1; cy = 1.8 + (i // 3) * 2.5
    card(s, cx, cy, 3.85, 2.38, title=t1, body=body, body_size=10.5, title_size=14, icon=ic, title_color=T["accent"] if ic == "KG" else T["primary"])
tb(s, 0.6, 6.78, 12, 0.3, "설치 목록 5줄: flask · langchain-core · langchain-openai · python-dotenv · pydantic (+ pandas · requests · tiktoken)", size=10.5, color=T["muted"])

# 7. ① ───────────────────────────────────────────────────────────
trial(5, "틀렸던 이야기 ① — AI는 시키면 채운다", "9/14 밤, 전공 102개 첫 시도",
    [[[("102개 전공 중 22개만 역량이 잡혔다", {"bold": True})], "컴퓨터공학부 = '보안' 하나", "간호학과 = '보안, 클라우드'", "통계학과 = 아무것도 없음"],
     ["\"근거 과목 2개 이상\" 규칙 — 대학 과목은 주제당 1개뿐", [("\"없으면 없다고 답해도 된다\"는 말이 없었다", {"bold": True}), (" → 간호학과에도 무언가를 붙임", {})], "AI가 과목명을 줄여 쓰면 근거로 안 쳐줌"],
     ["결과 파일을 눈으로 열어 봤다 — \"컴공 = 보안 하나\"는 누가 봐도 이상", [("같은 일이 4번 더: ", {"bold": True}), ("\"정확히 3개\", \"최대 5개\", \"3문장 이상\"이라고 시키면 채우려고 지어냈다", {})]],
     ["근거 과목 1개면 인정, 줄여 쓴 이름도 인정", "\"없으면 빈 칸이 정답\" + 틀린 예 4개를 보여줌", [("개수 지시 전부 삭제 — 근거가 1개면 1개만", {"bold": True})], "AI 답을 파일에 저장 → 규칙을 고칠 때 다시 안 물어봄 (0원)"]],
    "AI에게 \"없다\"라고 말할 권리를 주지 않으면, 있는 것처럼 말한다.")

# 8. ② — 이미지 ─────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 6, "틀렸던 이야기 ② — 글자가 같아야 이어진다", "9/15 낮, 전공과 직무가 공유하는 역량이 8개에서 멈췄다")
pic(s, "isa.png", 0.6, 1.8, w=7.4)
card(s, 8.3, 1.8, 4.4, 1.3, title="무슨 일이", body="직무는 Oracle·Java·AWS(도구 이름), 전공은 Database·Programming(학문 이름). 같은 뜻인데 글자가 달라 선이 안 이어졌다", body_size=11.5, icon="!", title_color=T["accent"])
card(s, 8.3, 3.25, 4.4, 1.3, title="어떻게 바꿨나", body="\"Oracle은 Database의 한 종류\" 같은 관계 102개를 사전에 적었다. 단 한 단계만, 위로만", body_size=11.5, icon="→", title_color=T["good"])
card(s, 8.3, 4.7, 4.4, 0.95, title="결과", body="공유 역량 8 → 30개 · 이어진 직무 역량 0 → 75개", body_size=11.5, icon="✓", title_color=T["primary"])
lesson(s, "거창한 온톨로지가 아니라 \"A는 B의 한 종류\" 100줄이었다. 대신 방향(위로만)을 지키는 게 전부.", y=6.0)
s.notes_slide.notes_text_frame.text = "왼쪽 그림: 공고의 말(빨강)과 과목의 말(초록)을 가운데 개념으로 잇는다. '위로만' — 전공이 Database를 가르친다고 Oracle을 안다고는 말하지 않는다."

# 9. ③ ───────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 7, "틀렸던 이야기 ③ — 눈 대신 정답지", "점수 계산을 세 번 바꿨다. 매번 \"이상한 1위\"가 알려줬다")
rows = [["시도", "이상한 1위", "왜", "어떻게 바꿨나"],
        ["1차: 겹치는 비율", "\"데이터 분석·통계\"에 식물생산과학부가 통계학과를 이김", "역량이 적은 전공이 유리", "학생 역량 중 채운 비율로"],
        ["2차: 드문 역량에 가중치", "과목 1개짜리 전공이 근거 19과목의 통계학과를 이김", "드문 역량을 너무 세게 침", "가중치를 줄이고, 과목이 적으면 덜 믿기"],
        ["3차: 직무 쪽", "역량 1개짜리 공고가 항상 만점", "적은 쪽이 유리한 같은 문제", "역량 2개 이상인 공고만"]]
table(s, 0.6, 1.85, 12.1, rows, [2.4, 4.3, 2.6, 2.8], font_size=11.5, row_h=0.62, first_col_bold=True)
card(s, 0.6, 4.6, 5.9, 1.2, title="알아채는 방법이 바뀌었다", body="눈으로 서너 개 보고 고치기 → 고칠 때마다 다른 데가 깨짐 → \"이 입력이면 이 전공\" 정답지 10개 → 24개", body_size=12, icon="◉")
card(s, 6.8, 4.6, 5.9, 1.2, title="정답지가 실제로 잡은 것", body="사전에 단어 하나 넣었더니 엉뚱한 직무가 1위 — 두 번 다 정답지가 먼저 알려줬다. 그 뒤 점수 계산은 손대지 않기로", body_size=12, icon="✓", title_color=T["good"])
lesson(s, "고치기 전에 정답지를 먼저 쓴다. 없으면 \"고쳤다\"와 \"옮겼다\"를 구분할 수 없다.", y=6.0)
s.notes_slide.notes_text_frame.text = "핵심은 점수식이 아니라 알아채는 방법. 정답지 24개가 자동으로 채점된다."

# 10. ④ ──────────────────────────────────────────────────────────
trial(8, "틀렸던 이야기 ④ — 한 단어의 무게", "9/16 저녁, 같은 자기소개에 결과가 실행마다 달랐다",
    [[[("같은 자기소개인데 강점이 실행마다 다르게 나왔다", {"bold": True})], "\"발표력·설득력\" ↔ \"분석력만\"", "그래서 1위 전공도 왔다 갔다"],
     [[("처음 짐작(틀림): ", {"bold": True, "color": T["accent"]}), ("\"규칙 100줄이 지워졌다\"", {})], [("두 버전을 나란히 비교하니 ", {}), ("차이는 '약점' 관련 몇 줄뿐", {"bold": True})], "① \"강점으로 나타남\" → \"강점으로 명확하게 나타남\"  ② 분류 선택지 3개 → 2개"],
     ["실험 3번 — 무엇을 되돌리면 안정되는지 하나씩", "가중치는 원인이 아니었다", "문구와 선택지를 되돌리니 두 번 연속 4/4"],
     [[("약점은 \"묻지 않는다\"만 하고, 분류 선택지는 남겨 둔다", {"bold": True})], "\"명확하게\"를 뺐다", [("AI는 같은 입력에도 조금씩 다르게 답한다 → 고치면 두 번 채점", {"bold": True})]]],
    "\"약점을 쓰지 않는다\"는 결정과 \"약점이란 단어를 지운다\"는 구현은 다른 일이었다. 첫 짐작은 틀렸고, 비교가 맞았다.")

# 11. ⑤ ──────────────────────────────────────────────────────────
trial(9, "틀렸던 이야기 ⑤ — 대화는 입력만", "질문 3개 → 팀원의 자기소개 분석 → 7가지를 묻는 대화",
    [[[("7가지를 다 물으니 8번 주고받기 · AI 20번 · 25초", {"bold": True})], "\"잘 모르겠어요\" 뒤에 같은 질문을 또 함", "같은 자기소개가 짧게 물으면 통계학과, 길게 물으면 컴퓨터공학부"],
     ["대화가 길수록 역량 단어가 늘어 1위가 흔들림", "전공을 고를 때 쓰는 건 관심·강점 두 가지뿐인데 일곱 가지를 다 물었다"],
     ["빈 자기소개로 직접 돌려 보며 횟수·시간을 셌다", "대화 방식 정답지 4개 추가"],
     [[("관심·강점만 묻고, 한 번씩만", {"bold": True}), (" → 2~3번 주고받기 · AI 6~8번", {})], [("지킨 선: 대화 중에 AI가 전공·직무를 말하지 않는다", {"bold": True}), (" — 그 순간 챗봇과 같아진다", {})]]],
    "더 많이 물으면 더 잘 아는 게 아니라, 더 많이 흔들렸다.")

# 12. ⑥ ──────────────────────────────────────────────────────────
trial(10, "틀렸던 이야기 ⑥ — 넷이 한 파일을 고치면", "9/16~17, 같은 파일을 두 사람이 같은 날 — 세 번",
    [["사전 파일을 두 사람이 같은 날 고침 → \"한 종류\" 관계 28줄이 사라짐", "한 사람이 카드를 숨겨 차별점이 화면에서 사라짐", "웹 고치기 4건을 두 사람이 동시에 → 같은 함수 충돌"],
     ["\"한 사람이 관리\"라고 정했지만 급하면 다들 고친다", "AI 도구로 편집하다 블록이 날아가도 자동 검사는 통과 (이름만 검사)", "\"설명서만 합친다\"가 실제론 전체를 합침"],
     [[("지도 만들 때 찍히는 숫자 \"이어진 역량 61 → 43\"", {"bold": True}), (" — 이게 경보였다", {})], "설명서에 적어 둔 \"왜 카드가 있어야 하나\"로 되돌림"],
     ["팀 요청 형식은 내용으로, 구조 개선은 틀로 — 합치는 원칙", "결정은 날짜 문서로 남긴다 (8개)", [("코드와 데이터를 따로, 받기 먼저", {"bold": True})]]],
    "역할을 나눠도 파일은 겹친다. 문서와 숫자가 없었으면 누가 맞는지 다투다 끝났을 것이다.")

# 13. 챗봇 대조 (1) — 뤼튼 vs ChatGPT ───────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 11, "챗봇 대조 (1) — 채우거나, 비우거나", "검색 끄고, 새 창에서, 우리 시연과 같은 문장을 넣었다 (9/17, 팀원이 각자)")
pic_fit(s, "chat_wrtn.png", 0.6, 1.7, 5.95, 4.05)
pic_fit(s, "chat_chatgpt.png", 6.75, 1.7, 5.95, 4.05)
rect(s, 0.6, 5.85, 5.95, 0.62, "FDECED", MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
tb(s, 0.8, 5.92, 5.6, 0.5, "뤼튼 — 그럴듯하게 채웠다. 과목 3개 중 2개는 3,829개 과목에 없고, 그 직무는 우리 공고에 없다", size=11.5, bold=True, color=T["accent"], anchor=MSO_ANCHOR.MIDDLE)
rect(s, 6.75, 5.85, 5.95, 0.62, T["card"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
tb(s, 6.95, 5.92, 5.6, 0.5, "ChatGPT — 솔직하게 비웠다. \"검증하지 않았다\", \"보장할 수 없다\"", size=11.5, bold=True, color=T["muted"], anchor=MSO_ANCHOR.MIDDLE)
tb(s, 0.6, 6.6, 12.1, 0.4, "고등학생은 이 둘을 구분할 방법이 없다. 근거 데이터가 있어야 \"안다\"와 \"그럴듯하다\"가 갈린다.   (대화 이미지는 답변 원문으로 재구성 — 실제 캡처로 교체 가능)", size=11, color=T["text"])
s.notes_slide.notes_text_frame.text = "왼쪽 뤼튼: 과목 이름과 직무를 자신 있게 말했지만, 우리 데이터에 없다. 물어보니 '특정 출처에서 가져온 게 아니다'라고 답했다. 오른쪽 ChatGPT: 같은 질문에 못 한다고 비웠다. 둘 다 학생더러 직접 확인하라고 했다."

# 13-2. 챗봇 대조 (2) — Gemini + 우리 ─────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 11, "챗봇 대조 (2) — Gemini, 그리고 우리 카드", "Gemini는 직무 이름을 맞혔지만, 과목과 직무 설명은 데이터와 어긋났다")
pic_fit(s, "chat_gemini.png", 0.6, 1.7, 5.95, 4.05)
rect(s, 0.6, 5.85, 5.95, 0.62, "FDECED", MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
tb(s, 0.8, 5.92, 5.6, 0.5, "Gemini — 과목 8개 중 4개 없음. DX 엔지니어를 \"데이터 분석\" 직무로 설명 (실제 공고는 개발 직무)", size=11.5, bold=True, color=T["accent"], anchor=MSO_ANCHOR.MIDDLE)
rows = [["", "우리 카드", "ChatGPT", "뤼튼", "Gemini"],
        ["전체 중 몇 위인지", "✓ 61개 중 1위", "✗ 답하지 않음", "✗ 순위 없음", "✗ 순위 없음"],
        ["과목이 실제로 있나", "✓ 전부", "있지만 \"검증 안 함\"", "✗ 3개 중 2개 없음", "✗ 8개 중 4개 없음"],
        ["공고가 요구하는 역량 개수", "✓ 2개 중 2개", "\"일반 기준\" 7개 중 4개", "✗ 출처 없이 단정", "✗ 설명이 어긋남"],
        ["같은 뜻 다른 말 → 같은 답", "✓ 정답지 매번 통과", "1위만 같고 목록은 매번 다름", "—", "—"]]
table(s, 6.75, 1.75, 5.95, rows, [1.75, 1.1, 1.1, 1.0, 1.0], font_size=9.5, row_h=0.5, first_col_bold=True)
card(s, 6.75, 4.5, 5.95, 1.95, title="챗봇이 잘한 것도 있다", body="\"패턴을 찾고 → 코드로 분석하고 → 설명하는 쪽에 강점\" 같은 해석과 문장은 ChatGPT가 잘 쓴다. 그래서 우리도 그 부분(설명 문단)은 AI에 맡긴다. 결론은 \"챗봇 대 우리\"가 아니라 \"말은 AI, 판정은 데이터\"", body_size=12, icon="✓", title_color=T["good"])
tb(s, 0.6, 6.6, 12.1, 0.4, "우리 카드: 61개 중 46개 비교 1위 · 과목 7개로 이어짐 · 요구 2/2 충족 · 출처 대학알리미·LG Careers — 전부 데이터에서 센 것", size=11, color=T["text"], bold=True)
s.notes_slide.notes_text_frame.text = "표는 전문(docs/20260917_챗봇_대조.md)의 판정표를 줄인 것. 결론이 같아도(통계학과) 근거가 다르다."

# 14. 비용 ────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 12, "비용 — 질문 한 번에 AI가 읽는 양", "토큰 = AI가 글을 세는 단위. 한글 한 글자가 대략 1토큰")
cd = CategoryChartData()
cd.categories = ["A. 챗봇에 그냥 묻기", "B. 데이터를 통째로 주고 묻기", "C. 우리 (지도를 읽기)"]
cd.add_series("질문 1번에 읽는 토큰", (500, 115000, 1400))
gf = s.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED, Inches(0.6), Inches(1.85), Inches(7.4), Inches(4.2), cd)
ch = gf.chart; ch.has_legend = False; ch.has_title = True
ch.chart_title.text_frame.text = "질문 1번에 AI가 읽는 토큰 (실측)"
r0 = ch.chart_title.text_frame.paragraphs[0].runs[0]; r0.font.size = Pt(12); r0.font.name = FONT; r0.font.color.rgb = rgb(T["text"])
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
card(s, 8.3, 1.85, 4.4, 1.35, title="약 85배 차이", body="B는 교육과정 전체와 공고 전체를 매번 읽는다. 우리는 미리 만든 지도만 읽는다", body_size=12, icon="÷")
card(s, 8.3, 3.35, 4.4, 1.35, title="지도 만들기는 한 번만", body="AI 277번 (B의 2~3번 분량). 3번째 질문부터 우리가 싸다", body_size=12, icon="1")
card(s, 8.3, 4.85, 4.4, 1.2, title="돈보다 큰 이유", body="B는 AI가 판정 → 매번 답이 다르고 개수를 못 센다", body_size=12, icon="=", title_color=T["accent"])
tb(s, 0.6, 6.35, 12, 0.5, "A는 데이터가 없어서 기억으로 답한다. 숫자 근거: docs/20260916_발표_수치_4-5장.md", size=11, color=T["muted"])

# 15. 한계 ────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 13, "한계 — 먼저 말합니다")
lims = [("대학이 서울대 하나", "\"어느 대학이 좋은가\"는 답 못 한다. \"서울대 교육과정 기준 어느 전공인가\"만"),
        ("과목 이름만 있다", "과목 설명이 없어 이름만 보고 판단. 그래서 전공 단위로 묶어 읽었다"),
        ("공고는 그날 받아 둔 것", "9/11·9/15 기준. LG CNS 신입 공고는 이미 닫혔다 — 날짜를 붙여 말한다"),
        ("사전 밖 직무 10개", "신입 85개 중. 어학·엑셀만 요구하는 사무직 등"),
        ("AI는 조금씩 다르게 답한다", "역량 뽑기·성향 읽기에서. 판정은 아니지만 정답지로 계속 감시"),
        ("어학은 점수 밖", "공고 32%가 요구하지만 \"자격\"이지 대학이 기르는 역량이 아니라서")]
for i, (t1, t2) in enumerate(lims):
    cx = 0.6 + (i % 3) * 4.1; cy = 1.7 + (i // 3) * 2.35
    card(s, cx, cy, 3.85, 2.1, title=t1, body=t2, body_size=12, title_size=14, icon=str(i + 1), title_color=T["primary"] if i % 2 == 0 else T["muted"])

# 16. 다른 팀에 묻고 싶은 것 ───────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 14, "다른 팀에 묻고 싶은 것 — 우리가 못 푼 문제 넷", "이 발표에서 우리가 가장 배우고 싶은 부분입니다")
qs = [("공통 사전(어휘)은 누가 어떻게 관리했나요?", "한 사람 담당으로 정했는데도 동시에 고치는 일이 생겼습니다."),
      ("AI 답이 조금씩 달라지는 건 어떻게 다뤘나요?", "무작위성을 꺼도 흔들렸습니다. 정답지를 두 번 돌리는 것 말고 더 나은 방법이 있을까요?"),
      ("판정을 AI에게 맡긴 팀은 어떻게 같은 답을 보장했나요?", "우리는 계산으로 넘겼는데, 그 대가로 말이 딱딱해졌습니다."),
      ("사용자 입력을 어디까지 대화로 받았나요?", "우리는 길어질수록 결과가 흔들려 두 가지만 물었습니다.")]
for i, (q, d) in enumerate(qs):
    cy = 1.9 + i * 1.22
    rect(s, 0.6, cy, 12.1, 1.05, T["card"], MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08)
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.85), Inches(cy + 0.27), Inches(0.5), Inches(0.5))
    o.fill.solid(); o.fill.fore_color.rgb = rgb(T["accent"]); o.line.fill.background(); etree.SubElement(o._element.spPr, qn("a:effectLst"))
    tf = o.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = "Q"; r.font.bold = True; r.font.size = Pt(14); r.font.color.rgb = rgb("FFFFFF"); r.font.name = "Arial"
    tb(s, 1.6, cy + 0.15, 10.9, 0.4, q, size=15, bold=True, color=T["text"])
    tb(s, 1.6, cy + 0.55, 10.9, 0.45, d, size=12, color=T["muted"])

# 17. 역할·회고 ────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, 15, "역할과 회고 — 각자 \"가장 크게 틀렸던 것\"", "이름과 회고는 팀원이 직접 채웁니다")
rows = [["역할", "이름", "맡은 것", "가장 크게 틀렸던 것", "다음엔"],
        ["A · 사전·PM", "(이름)", "공통 사전 139단어 · '한 종류' 관계 102", "(직접 작성)", "(직접 작성)"],
        ["B · 계산·통합", "(이름)", "전공·직무·과목 고르는 계산 · 코드 합치기", "(직접 작성)", "(직접 작성)"],
        ["C · 데이터", "(이름)", "공고 수집 · AI로 역량 뽑기 · 지도 만들기", "(직접 작성)", "(직접 작성)"],
        ["D · 화면", "(이름)", "카드·설명 문단 · 대화 · 웹 · 정답지", "(직접 작성)", "(직접 작성)"]]
table(s, 0.6, 1.9, 12.1, rows, [1.8, 1.4, 3.6, 2.9, 2.4], font_size=11.5, row_h=0.72, first_col_bold=True)
card(s, 0.6, 5.75, 12.1, 0.95, body="예시 (실제로 있었던 것): \"규칙이 지워진 줄 알았는데 비교해 보니 한 단어였다\" · \"설명서만 합친 줄 알았는데 전체였다\" · \"일곱 가지를 다 물으면 더 정확할 줄 알았다\"", body_size=12)

# 18. 마무리 ──────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, W, H, T["dark"])
node_motif(s, 11.3, 0.5, scale=1.2, colors=["5B6BC4", T["accent"], "5B6BC4"])
tb(s, 0.9, 0.7, 10, 0.7, "배운 문장 여섯 개", size=30, bold=True, color=T["dark_text"])
lessons = ["AI에게 \"없다\"라고 말할 권리를 주지 않으면, 있는 것처럼 말한다.",
           "온톨로지는 \"A는 B의 한 종류\" 100줄이었다. 방향(위로만)을 지키는 게 전부.",
           "고치기 전에 정답지를 먼저 쓴다. 없으면 \"고쳤다\"와 \"옮겼다\"를 구분할 수 없다.",
           "\"약점을 쓰지 않는다\"는 결정과 \"약점이란 단어를 지운다\"는 구현은 다른 일이다.",
           "더 많이 물으면 더 잘 아는 게 아니라, 더 많이 흔들렸다.",
           "역할을 나눠도 파일은 겹친다. 문서와 숫자가 없었으면 다투다 끝났을 것이다."]
for i, l in enumerate(lessons):
    y = 1.7 + i * 0.78
    o = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.9), Inches(y + 0.08), Inches(0.42), Inches(0.42))
    o.fill.solid(); o.fill.fore_color.rgb = rgb(T["accent"]); o.line.fill.background(); etree.SubElement(o._element.spPr, qn("a:effectLst"))
    tf = o.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = str(i + 1); r.font.bold = True; r.font.size = Pt(12); r.font.color.rgb = rgb("FFFFFF"); r.font.name = "Arial"
    tb(s, 1.55, y + 0.1, 11.0, 0.5, l, size=16, color=T["dark_text"])
tb(s, 0.9, 6.55, 11.5, 0.5, "감사합니다 — 코드·문서·결정 기록: github.com/KU-CS-HTG/LG-CNS-KG-Project-1", size=12, color=T["dark_muted"])

# 부록 A ───────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, None, "부록 A — 예상 질문과 답")
rows = [["질문", "답"],
        ["왜 어학이 없나요? 영업엔 외국어가 핵심인데", "어학은 역량이 아니라 지원 자격(예: OPIc 몇 등급 이상). 대학 과목으로 영어를 \"기르는\" 전공이 없고, 점수에 넣으면 어학을 적은 직무만 불리해진다. 정보로 보여 주는 건 다음 과제"],
        ["왜 서울대만?", "교육과정 데이터가 한 곳. 대학을 비교하는 게 아니라 \"서울대 교육과정 기준으로 어느 전공\"을 답한다"],
        ["LG CNS 신입 공고가 닫혔는데?", "9/11에 받아 둔 공고. 그래서 \"없다\"가 아니라 \"이 날짜 기준\"이라고 말한다"],
        ["ChatGPT에 물으면 안 되나요?", "결론(통계학과)은 같을 수 있다. 다른 건 근거 — \"46개 중 1위, 과목 7개, 요구 2개 중 2개\"를 세어서 보여주는 것과 \"1위 후보로 봅니다\"는 다르다"],
        ["AI는 어디에 쓰나요?", "글에서 역량 이름을 뽑을 때와 카드를 풀어 쓸 때. 어떤 전공·직무를 고를지는 계산이 한다"],
        ["46%가 무슨 뜻인가요?", "\"어울릴 확률\"이 아니라 학생 역량이 그 전공 과목과 이어진 정도. 1위가 22%인 입력도 있다"]]
table(s, 0.6, 1.6, 12.1, rows, [4.0, 8.1], font_size=11, row_h=0.68, first_col_bold=True)

# 부록 B ───────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
header(s, None, "부록 B — 숫자와 문서")
rows = [["항목", "값"],
        ["입력", "서울대 105 전공 · 과목 3,829 / LG 계열사 9곳 · 공고 50 → 직무 172 (신입 85)"],
        ["지도", "전공 61 · 직무 108 (신입 75) · 역량 120 · 관계 5종 (\"기른다\" 174 · \"요구한다\" 447 · \"한 종류\" 102 · 성향 관계 24)"],
        ["사전", "대표 단어 139 · 다른 표기 417 · 상위 개념 23"],
        ["AI 호출", "지도 만들기 277번 (한 번) · 학생 1명당 2~6번 · 자동 채점 1회 약 45번"],
        ["검증", "확인 3가지 · 정답지 24개 전부 통과 (두 번 연속)"]]
table(s, 0.6, 1.6, 12.1, rows, [1.8, 10.3], font_size=11, row_h=0.6, first_col_bold=True)
card(s, 0.6, 5.45, 12.1, 1.4, title="결정 기록 (저장소 docs/, 날짜순)", body=[
    "09-15  전공 추출 필터 수정 · 온톨로지 계층", "09-16  어휘 3단계 · 대화형 입력 검토 · 카드 형식 · 인터뷰 평가 회귀 분석 · 발표 수치 · 시연 대본",
    "09-17  발표 내용 취합 · 챗봇 대조 실험 · 쉽게 읽는 소개 · 프로젝트 설명서(12장)"], body_size=11.5, icon="D")

out = sys.argv[1] if len(sys.argv) > 1 else "deck_v2.pptx"
prs.save(out); print("saved", out, len(prs.slides), "slides")
