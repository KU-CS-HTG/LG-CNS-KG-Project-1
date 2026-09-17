# -*- coding: utf-8 -*-
"""슬라이드용 이미지 생성 (PIL): 흐름도 · '한 종류' 관계 · 챗봇 대화 카드 3장. 팔레트 = Graph Ink."""
from PIL import Image, ImageDraw, ImageFont
import textwrap, os

C = dict(text=(31, 36, 48), muted=(107, 114, 128), primary=(47, 60, 126), accent=(249, 97, 103), good=(26, 158, 122),
         card=(243, 244, 248), card2=(238, 241, 251), white=(255, 255, 255), line=(200, 204, 214), stud=(230, 247, 239), bot=(242, 246, 255))
F = "C:/Windows/Fonts/malgun.ttf"; FB = "C:/Windows/Fonts/malgunbd.ttf"
def font(size, bold=False): return ImageFont.truetype(FB if bold else F, size)
OUT = os.path.dirname(os.path.abspath(__file__)) + "/img"; os.makedirs(OUT, exist_ok=True)


def rrect(d, box, fill, r=28, outline=None, width=3):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width if outline else 0)


def text_center(d, cx, cy, s, f, fill):
    w = d.textlength(s, font=f); h = f.size
    d.text((cx - w / 2, cy - h / 2), s, font=f, fill=fill)


def arrow(d, x1, y1, x2, y2, color, w=6, head=22):
    d.line((x1, y1, x2, y2), fill=color, width=w)
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    p1 = (x2 - head * math.cos(ang - 0.45), y2 - head * math.sin(ang - 0.45))
    p2 = (x2 - head * math.cos(ang + 0.45), y2 - head * math.sin(ang + 0.45))
    d.polygon([(x2, y2), p1, p2], fill=color)


def wrap_lines(d, s, f, maxw):
    lines = []
    for para in s.split("\n"):
        cur = ""
        for ch in para:
            if d.textlength(cur + ch, font=f) > maxw and cur:
                lines.append(cur); cur = ch
            else:
                cur += ch
        lines.append(cur)
    return lines


# ── 1. 흐름도 ─────────────────────────────────────────────────────
def flow():
    W, H = 2600, 1100
    im = Image.new("RGB", (W, H), C["white"]); d = ImageDraw.Draw(im)
    fT, fB, fS = font(40, True), font(30, True), font(26)

    def box(x, y, w, h, title, sub, fill, tcol):
        rrect(d, (x, y, x + w, y + h), fill)
        text_center(d, x + w / 2, y + h * 0.36, title, fB, tcol)
        for i, l in enumerate(wrap_lines(d, sub, fS, w - 40)):
            text_center(d, x + w / 2, y + h * 0.62 + i * 34, l, fS, C["muted"])

    # 상단: 지도 만들기 (한 번만)
    t1 = "① 지도 만들기 — 미리, 한 번만"; d.text((60, 40), t1, font=fT, fill=C["primary"])
    d.text((60 + d.textlength(t1, font=fT) + 40, 52), "AI가 글을 읽어 역량 이름을 뽑는다 (총 277번, 결과는 저장해 둠)", font=fS, fill=C["muted"])
    y = 130; h = 190
    box(60, y, 440, h, "과목 이름 3,829개", "서울대 105개 전공\n(대학알리미)", C["card"], C["text"])
    box(60, y + 230, 440, h, "채용 공고 172개", "LG 계열사 9곳\n(careers.lg.com)", C["card"], C["text"])
    arrow(d, 510, y + h / 2, 640, y + 200, C["line"]); arrow(d, 510, y + 230 + h / 2, 640, y + 220, C["line"])
    box(650, y + 105, 520, 210, "AI가 역량 이름 뽑기", "\"통계학과는 통계·데이터 분석을 기른다\"\n\"이 직무는 머신러닝을 요구한다\"", C["card2"], C["primary"])
    arrow(d, 1180, y + 210, 1300, y + 210, C["line"])
    box(1310, y + 105, 560, 210, "사전으로 이름 통일", "같은 뜻은 한 단어로 (139개)\n\"Oracle은 Database의 한 종류\" (102개)", C["card2"], C["primary"])
    arrow(d, 1880, y + 210, 2000, y + 210, C["line"])
    box(2010, y + 80, 530, 260, "지도 완성", "전공 61 — 역량 120 — 직무 108\n관계 5종", (223, 232, 244), C["primary"])

    # 구분선
    d.line((60, 600, W - 60, 600), fill=C["line"], width=3)

    # 하단: 지도 읽기 (학생이 올 때마다)
    t2 = "② 지도 읽기 — 학생이 올 때마다"; d.text((60, 630), t2, font=fT, fill=C["primary"])
    d.text((60 + d.textlength(t2, font=fT) + 40, 642), "판정은 AI가 아니라 사전 찾기와 '겹치는 것 세기'가 한다", font=fS, fill=C["muted"])
    y = 730; h = 200; w = 360; gap = 66
    steps = [("학생 이야기", "자기소개나\n질문 3개", C["card"], C["text"]),
             ("역량 태그", "AI 1번 — 사전에\n있는 단어만", C["card2"], C["primary"]),
             ("전공 1위", "61개 전부 비교\n예) 통계학과", C["card2"], C["primary"]),
             ("직무", "전공이 기르는 역량으로\n충족/부족 세기", C["card2"], C["primary"]),
             ("과목 3개", "전공과 직무를\n잇는 다리", C["card2"], C["primary"]),
             ("카드 + 설명", "숫자·근거는 카드\n말은 AI 1번", (223, 232, 244), C["primary"])]
    for i, (t, s, fill, col) in enumerate(steps):
        x = 60 + i * (w + gap)
        box(x, y, w, h, t, s, fill, col)
        if i < len(steps) - 1:
            arrow(d, x + w + 8, y + h / 2, x + w + gap - 8, y + h / 2, C["line"])
    # 판정 구간 표시
    x1 = 60 + 2 * (w + gap); x2 = 60 + 5 * (w + gap) - gap
    d.rounded_rectangle((x1 - 14, y + h + 26, x2 + 14, y + h + 90), radius=20, fill=C["stud"])
    text_center(d, (x1 + x2) / 2, y + h + 58, "이 세 칸에는 AI가 없다 → 같은 이야기에 같은 답 · 카드의 이름은 전부 실제 데이터", font(26, True), C["good"])
    im.crop((0, 0, W, 1030)).save(f"{OUT}/flow.png")


# ── 2. '한 종류' 관계 ────────────────────────────────────────────
def isa():
    W, H = 1800, 900
    im = Image.new("RGB", (W, H), C["white"]); d = ImageDraw.Draw(im)
    fB, fS, fH = font(34, True), font(26), font(30, True)
    d.text((60, 40), "채용 공고가 쓰는 말", font=fH, fill=C["accent"])
    d.text((1180, 40), "대학 과목이 쓰는 말", font=fH, fill=C["good"])
    pairs = [("Oracle", "Database", "데이터베이스"), ("Java", "Programming", "프로그래밍방법론"), ("AWS", "Cloud", "클라우드컴퓨팅")]
    for i, (job, mid, subj) in enumerate(pairs):
        y = 130 + i * 230
        rrect(d, (60, y, 460, y + 150), (253, 236, 237)); text_center(d, 260, y + 75, job, fB, C["accent"])
        rrect(d, (700, y, 1100, y + 150), C["card2"]); text_center(d, 900, y + 75, mid, fB, C["primary"])
        rrect(d, (1340, y, 1740, y + 150), C["stud"]); text_center(d, 1540, y + 75, subj, fB, C["good"])
        arrow(d, 470, y + 75, 690, y + 75, C["primary"])
        text_center(d, 580, y + 40, "~의 한 종류", fS, C["muted"])
        arrow(d, 1330, y + 75, 1110, y + 75, C["good"])
        text_center(d, 1220, y + 40, "이 과목이 기른다", fS, C["muted"])
    d.rounded_rectangle((60, 830, 1740, 890), radius=20, fill=C["card"])
    text_center(d, 900, 860, "규칙: 한 단계만 · 위로만 (Oracle → Database는 참, Database를 배웠다고 Oracle을 안다고 말하지 않는다)", font(26, True), C["text"])
    im.save(f"{OUT}/isa.png")


# ── 3. 챗봇 대화 카드 ────────────────────────────────────────────
def chat(name, meta, turns, marks=None, fname="chat.png", note="답변 원문에서 재구성 — 실제 화면 캡처로 교체 가능"):
    """turns: [(who, text), ...] who ∈ {'me','bot'}. marks: 강조할 문자열 → 색."""
    W = 1500; f = font(31); fb = font(31, True); fh = font(34, True); fm = font(24)
    pad = 40; maxw = 1180
    # 높이 계산
    items = []
    total = 150
    for who, txt in turns:
        lines = wrap_lines(ImageDraw.Draw(Image.new("RGB", (10, 10))), txt, f, maxw - 60)
        h = 44 + len(lines) * 46
        items.append((who, lines, h)); total += h + 30
    total += 70
    im = Image.new("RGB", (W, total), C["white"]); d = ImageDraw.Draw(im)
    rrect(d, (0, 0, W - 1, total - 1), C["white"], r=30, outline=C["line"], width=3)
    # 헤더
    d.rounded_rectangle((0, 0, W - 1, 100), radius=30, fill=C["card"]); d.rectangle((0, 60, W - 1, 100), fill=C["card"])
    d.ellipse((pad, 25, pad + 50, 75), fill=C["primary"]); text_center(d, pad + 25, 50, name[0], font(26, True), C["white"])
    d.text((pad + 70, 28), name, font=fh, fill=C["text"]); d.text((pad + 70 + d.textlength(name, font=fh) + 20, 38), meta, font=fm, fill=C["muted"])
    y = 130
    for who, lines, h in items:
        bw = max(d.textlength(l, font=f) for l in lines) + 60
        if who == "me":
            x1 = W - pad - bw; fill = C["stud"]
        else:
            x1 = pad; fill = C["bot"]
        rrect(d, (x1, y, x1 + bw, y + h), fill, r=26)
        for i, l in enumerate(lines):
            d.text((x1 + 30, y + 22 + i * 46), l, font=f, fill=C["text"])
            if marks:
                for key, col in marks.items():
                    if key in l:
                        kx = x1 + 30 + d.textlength(l[:l.index(key)], font=f); kw = d.textlength(key, font=f)
                        d.line((kx, y + 22 + i * 46 + 42, kx + kw, y + 22 + i * 46 + 42), fill=col, width=5)
        y += h + 30
    d.text((pad, total - 52), note, font=fm, fill=C["muted"])
    im.save(f"{OUT}/{fname}")


ME = "고등학생이고 진로를 고민 중이에요. 수학이랑 통계를 좋아하고, 설문 데이터를 파이썬으로 분석해 발표해 봤어요. 맞는 대학 전공이랑 LG 계열사 신입 직무를 추천해 주세요."

chat("뤼튼", "2026-09-17 14:57 · 비로그인 · 검색 금지 요청", [
    ("me", ME),
    ("bot", "통계학, 수학과, 데이터사이언스 전공이 완전 딱 맞아! 대학에서 꼭 배우면 좋은 과목 3가지는\n- 확률과 통계\n- 데이터 분석 입문\n- 프로그래밍(파이썬 활용)"),
    ("bot", "LG CNS 데이터 분석 직무를 추천해! 실제로 이 직무에서 요구하는 주요 역량은 통계 이해, 코딩(Python 등), 대용량 데이터 처리, 그리고 의사소통 능력이야."),
    ("me", "관련해서 전공 과목에 대한 정보는 어디서 가지고 온거야?"),
    ("bot", "내가 말한 전공 과목 정보는 실제 특정 출처에서 가져온 게 아니라, 보통 대학교의 … 학과에서 공통적으로 개설하는 과목들을 기반으로 알려준 거야."),
], marks={"데이터 분석 입문": C["accent"], "프로그래밍(파이썬 활용)": C["accent"], "LG CNS 데이터 분석 직무": C["accent"], "실제 특정 출처에서 가져온 게 아니라": C["accent"]}, fname="chat_wrtn.png")

chat("ChatGPT", "5.6 · 임시 채팅 · 검색 끔 · 2026-09-17", [
    ("me", "웹 검색은 계속 사용하지 말고, 아래 형식으로 답해 주세요. 1. 서울대 전체 전공 중 순위 2. 실제 개설 과목명 3개 3. 맞는 LG 신입 직무와 요구 역량 개수 4. 출처 URL"),
    ("bot", "서울대 전체 전공의 정확한 개수, 현재 실제 개설 과목명, 특정 LG 신입 채용공고의 요구사항과 URL은 … 사실처럼 만들어낼 수 없습니다."),
    ("bot", "1위 후보로 통계학과를 봅니다. 다만 '전체 몇 개 전공 중 1위'의 정확한 숫자는 답하지 않겠습니다."),
    ("bot", "과목: 회귀분석 · 수리통계학 · 다변량자료분석 — 실제로 이 정확한 한글 과목명으로 개설되어 있는지는 웹 없이 검증하지 않았습니다."),
    ("bot", "'전체 N개 중 1위', '실제 개설 과목 3개', '실제 채용공고의 요구 역량 N개', '출처 URL'은 모두 외부 원문 확인이 필요한 항목이라 정확성을 보장할 수 없습니다."),
], marks={"사실처럼 만들어낼 수 없습니다": C["primary"], "정확한 숫자는 답하지 않겠습니다": C["primary"], "검증하지 않았습니다": C["primary"]}, fname="chat_chatgpt.png")

chat("Gemini", "임시 채팅 · 검색 금지 요청 · 2026-09-17", [
    ("me", ME),
    ("bot", "추천 대학 전공: 통계학과 / 데이터사이언스학과 · 산업공학과 · 빅데이터/AI 융합 관련 전공 (표로 3개, 순위 없음)"),
    ("bot", "LG CNS – DX 엔지니어 / AI·데이터 컨설턴트: 데이터를 분석해 고객사나 다른 LG 계열사의 문제를 해결해 주는 직무가 잘 맞습니다."),
    ("me", "통계학과의 실제 개설 과목명을 알려 주세요."),
    ("bot", "실제 대표 대학들의 공식 개설 과목명을 기준으로: 통계학원론 · 수리통계학 1, 2 · 회귀분석 및 실습 · 통계프로그래밍언어 · 데이터시각화 · 빅데이터분석 및 실습"),
], marks={"통계학원론": C["accent"], "통계프로그래밍언어": C["accent"], "데이터시각화": C["accent"], "빅데이터분석 및 실습": C["accent"], "데이터를 분석해 고객사나": C["accent"]}, fname="chat_gemini.png")

flow(); isa()
print("images:", sorted(os.listdir(OUT)))
