"""app.py — 온라인 파이프라인 (담당: D)"""
from __future__ import annotations

import json
import os
import unicodedata
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from vocab import CANON
from graph_store import (find_majors_by_skills, find_jobs_by_skills,
                         subjects_for, count_majors, taggable_skills,
                         find_jobs_by_name, find_majors_for_job)

load_dotenv()

# 태그 목록은 사전(CANON) 전체가 아니라 **그래프에 실제로 있는 역량**만.
#   사전에는 있지만 그래프엔 없는 역량(Problem Solving, Communication, Knowledge Graph — 전공 쪽 제외)이 태그가 되면
#   어느 전공과도 안 맞으면서 커버리지 분모만 키운다. 실측(9/15): 3태그 중 1개가 그런 태그라 상위권이 전부 0.82 동점.
TAGS: list[str] = taggable_skills()


def _korean_examples(skills: list[str], limit: int) -> str:
    """질문에 보여줄 예시를 어휘집에서 뽑는다. CANON 의 한글 별칭을 역으로 찾아 한국어로.

    질문은 사용자를 우리 어휘 안으로 유도해야 한다 — '잘하는 것 → 독서' 처럼 어휘 밖 답은 태그 0개다.
    예시를 어휘집에서 뽑으면 A 가 어휘를 바꿔도 질문이 따라간다.
    """
    korean = {}
    for alias, canon in CANON.items():
        if canon in skills and canon not in korean and any("가" <= ch <= "힣" for ch in alias):
            korean[canon] = alias.replace(" ", "")
    return ", ".join(list(korean.values())[:limit])


# 예시 우선순위: 상위 개념(PARENT 의 값) → 전공 쪽에 실제로 있는 것. 데이터/AI/개발/인프라/보안이 고루 나오게.
_Q1_EXAMPLES = _korean_examples(
    [s for s in ["Data Analysis", "Machine Learning", "Software Engineering", "Cloud", "Security", "Network",
                 "Signal Processing", "Statistics"] if s in TAGS], limit=6)

# 페르소나: 진로를 탐색하는 고등학생 (팀 결정 2026-09-15). 말투는 user_analysis/profile_config.py 의 질문 톤에 맞춘다.
QUESTIONS = [
    f"요즘 관심 있거나 해보고 싶은 분야가 있어? (예: {_Q1_EXAMPLES})",
    "수업이나 프로젝트, 써 본 도구 중에 직접 해본 게 있으면 알려줘. (예: 파이썬으로 데이터 정리, 통계 수업, 웹사이트 만들기)",
    "다음 중 더 끌리는 쪽은? ① 데이터를 파고들어 패턴 찾기 "
    "② 시스템을 설계하고 만들기 ③ 사람과 일정을 조율해 프로젝트 굴리기",
]
FOLLOWUP_PREFIX = "조금 더 알려줄래? "

class Tags(BaseModel):
    # 하한을 두지 않는다 — "최대 5개"만 있어도 모델은 5개를 채우려 든다 (9/15 실측: '숫자에 강해요' → Cloud까지 채움).
    # 전공 추출의 "4~8개", my_service의 "정확히 3개"와 같은 함정. 개수는 근거가 정한다.
    tags: list[str] = Field(description="답변에 직접 근거가 있는 태그만. 근거 없으면 넣지 않는다. 최대 5개", max_length=5)

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_TAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "사용자 답변에서 역량 태그를 뽑습니다.\n"
     "반드시 다음 목록에 있는 태그만 사용하세요: {tag_list}\n"
     "규칙:\n"
     "1. 답변에 **직접 근거가 있는 태그만** 고릅니다. '숫자에 강하다'는 Statistics의 근거는 되지만 Cloud의 근거는 아닙니다.\n"
     "2. 개수를 채우려 하지 마세요. 근거가 1개면 1개만 냅니다. 보통 1~3개입니다. 최대 5개.\n"
     "3. 목록에 없는 말은 만들지 마세요."),
    ("human", "{answers}"),
])
_tagger = _TAG_PROMPT | _llm.with_structured_output(Tags)


# Q3 는 선택지가 정해져 있으므로 LLM 없이 태그로 직접 매핑한다.
#   실측(9/15): "2" 라고 답해도 LLM 태거가 Software Engineering 을 못 뽑았다. 정해진 답은 정해진 규칙으로 — 도구가 판정한다.
Q3_TAGS: dict[str, list[str]] = {
    "1": ["Data Analysis"],
    "2": ["Software Engineering"],
    "3": ["Project Management"],
}
_Q3_KEY = str.maketrans("①②③", "123")


def q3_to_tags(answer: str) -> list[str]:
    key = (answer or "").strip().translate(_Q3_KEY)[:1]
    return [t for t in Q3_TAGS.get(key, []) if t in set(TAGS)]


def normalize_to_tags(answers: list[str]) -> list[str]:
    """답변 → 통제 어휘 태그. 목록 밖 태그는 2중으로 걸러낸다. (Q3 는 규칙, 나머지는 LLM 1회)"""
    free = [a for i, a in enumerate(answers) if i != 2]        # Q1, Q2, (재질문 답)
    q3 = answers[2] if len(answers) > 2 else ""
    res = _tagger.invoke({"tag_list": ", ".join(TAGS),
                          "answers": "\n".join(free)})
    llm_tags = [t for t in res.tags if t in set(TAGS)]
    return list(dict.fromkeys(llm_tags + q3_to_tags(q3)))     # 순서 유지 + 중복 제거


TRAIT_TAG_WEIGHT = 0.5   # 성향에서 추정한 태그 — 근거가 아니라 연관에서 온 것이라 절반만 믿는다 (vocab.TRAIT_TO_SKILL 참고)


def run(answers: list[str], session: dict, trait_tags: list[str] | None = None,
        stated_tags: list[str] | None = None, soft_traits: list[str] | None = None,
        profile_summary: str | None = None) -> dict:
    """answers: [Q1, Q2] (--basic 모드에서만 Q3 포함).
    인터뷰 모드 전용 (선택):
      stated_tags     — 관심 분야를 사전으로 직접 바꾼 태그 + 성향 판단 태그(interview.infer_orientation).
                        학생이 말한 것과 같은 무게(1.0)
      trait_tags      — 성향→기술 역량으로 추정한 태그. 연관일 뿐이라 0.5
      soft_traits     — 강점 성향(한글). 직무의 요구 태도와 대조 (동점 처리 전용, 점수 아님)
      profile_summary — [진로 추천] 문단에 배경으로 쓸 프로필 요약 (interview.profile_summary_text)
    """
    tags = list(dict.fromkeys([t for t in (stated_tags or []) if t in set(TAGS)] + normalize_to_tags(answers)))

    if len(tags) < 2 and not session.get("asked_again"):     # 조건부 분기, 1회
        session["asked_again"] = True
        return {"followup": QUESTIONS[0]}

    session["tags"] = list(dict.fromkeys(session.get("tags", []) + tags))
    tags = session["tags"]

    # 성향 태그: 근거 태그와 겹치지 않는 것만 0.5 로 추가. 화면에는 따로 표시한다
    inferred = [t for t in (trait_tags or []) if t in set(TAGS) and t not in tags]
    weights = {t: TRAIT_TAG_WEIGHT for t in inferred}

    # ① 전공 — limit을 크게 줘서 순위를 전부 받는다
    ranking = find_majors_by_skills(tags + inferred, limit=100, tag_weights=weights)
    if not ranking:
        return {"tags": tags, "empty": True}
    major = ranking[0]

    # ② 직무 — 사용자 태그가 아니라 '전공이 기르는 역량 **전체**'로 찾는다 ★ (설계서 4절 ②, 가이드 D-3)
    #    evidence 는 태그와 매칭된 역량만 담고 있어서 그걸 넘기면 직무 추천이 태그에 끌려간다.
    #    실측(9/15): 태그 1개(Data Analysis)만 넘어가 역량 2개짜리 Consulting 이 매번 1위 — 전공의 나머지 5개 역량이 버려졌다.
    major_skills = major["skills"]
    jobs = find_jobs_by_skills(major_skills, limit=3, career_type="신입", soft_traits=soft_traits)   # 정의: 신입 직무 추천. 1위 + 다음 후보 2개 (render 의 [다음 후보])
    if not jobs:                                                            # 신입 공고와 안 이어지면 전체에서
        jobs = find_jobs_by_skills(major_skills, limit=3, soft_traits=soft_traits)
    job = jobs[0] if jobs else None

    # ③ 다리 과목 — 직무가 요구하고 전공도 가진 역량 기준.
    #    정확 일치(have) + 계열 일치에 쓰인 전공 쪽 상위 개념(family 의 값. 예: Oracle 을 커버한 Database)
    if job:
        bridge = sorted(set(major_skills) & (set(job["have"]) | set(job["family"].values())))
    else:
        bridge = major_skills
    subjects = subjects_for(major["id"], bridge, k=3)
    if len(subjects) < 3:                                      # 다리 과목이 부족하면 전공 역량 전체로 보강
        subjects = subjects_for(major["id"], major_skills, k=3)

    return {"tags": tags, "inferred_tags": inferred, "ranking": ranking, "total_majors": count_majors(),
            "major": major, "job": job, "jobs": jobs, "subjects": subjects, "profile_summary": profile_summary}


# ── 카드 헬퍼 (LLM 없음). 카드 = 사실(숫자·근거), 문단 = 말(LLM) — docs/20260916_render_v2_스펙.md
BAR_WIDTH = 10
SOURCE_URLS = {                              # 카드 끝 출처 줄. 과목은 대학알리미 공시 xlsx 를 정리한 것(설명서 5-1), 공고는 careers.lg.com 스냅샷(data/raw/)
    "curriculum": "https://www.academyinfo.go.kr",
    "jobs": "https://careers.lg.com",
}


def _pct(score: float) -> int:
    """0.4632 → 46. 전공 점수(√idf 가중 커버리지, 0~1)를 백분율로. 확률이 아니므로 라벨은 '역량 연결도' 로만 쓴다."""
    return round(score * 100)


def _bar(score: float, width: int = BAR_WIDTH) -> str:
    filled = round(min(max(score, 0.0), 1.0) * width)
    return "█" * filled + "░" * (width - filled)


def _disp_width(s: str) -> int:
    """터미널 표시 폭 — 한글·전각은 2칸. len() 으로 맞추면 '통계학과' 와 '화학생물공학부' 의 바가 어긋난다."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


LINE_WIDTH = 72   # 웹 details.html 의 <pre>(640px − 패딩, 13px 모노)가 한 줄에 보여주는 폭 — 영문 ≈78칸, 한글은 2칸으로 세므로 72 면 안전.
                  # 넘는 줄은 의미 단위(항목 사이)로만 나눈다 (9/16 웹 시연 피드백)


def _wrap_items(prefix: str, items: list[str], indent: str, sep: str = ", ") -> list[str]:
    """`prefix + items 를 sep 으로 이은 것` 을 LINE_WIDTH 안에서 항목 경계로만 나눈다. 항목 하나가 잘리는 일은 없다.
    이어지는 줄은 prefix 의 표시 폭만큼 들여 써서 항목의 세로선이 맞는다.

    예: _wrap_items("✓ ", ["Data Analysis", …], IND) → ["          ✓ Data Analysis, Statistics, …", "            Machine Learning"]
    """
    lines: list[str] = []
    cur = indent + prefix
    # 이어지는 줄의 들여쓰기: 접두어가 짧으면("✓ ", "○ ") 그 폭만큼, 길면("≈ Machine Learning 계열로 커버 — ") 2칸만 —
    # 긴 접두어 폭만큼 들여 쓰면 남는 폭이 30칸도 안 돼 항목이 한두 개씩 뚝뚝 끊긴다 (9/17 병합 때 실측)
    pw = _disp_width(prefix)
    cont = indent + " " * (pw if pw <= 8 else 2)
    first = True
    for it in items:
        piece = it if first else sep + it
        if not first and _disp_width(cur) + _disp_width(piece) > LINE_WIDTH:
            lines.append(cur.rstrip())
            cur, piece = cont, it
        cur += piece
        first = False
    lines.append(cur.rstrip())
    return lines


def _pretty(name: str) -> str:
    """'전기?정보공학부' → '전기·정보공학부'. CSV 를 CP949 → UTF-8 로 옮길 때 '·' 가 '?' 로 깨진 전공명 5개 — 데이터는 그대로 두고 표시만 고친다
    (graph.json 의 이름을 바꾸면 majors_raw 캐시 키가 어긋나 LLM 재호출이 생긴다). check.py 의 .replace("?", "·") 와 같은 처리."""
    return name.replace("?", "·")


def _one_school(r: dict) -> bool:
    """데이터에 학교가 한 곳뿐이면 학교 이름은 정보량이 0 (그리고 박탈감을 줄 수 있다 — 9/16 팀 논의).
    하드코딩으로 빼지 않고 규칙으로 숨긴다 — 학교가 늘면 자동으로 다시 보인다."""
    return len({m["school"] for m in r["ranking"]}) == 1


def _job_status_items(j: dict) -> list[str]:
    """요구 역량 전체를 'skill(O)' / 'skill(X)' 항목으로. ≈(계열로 커버)도 충족(O)으로 센다 — 9/16 팀 요청."""
    have, fam, gap = set(j["have"]), j.get("family", {}), set(j["gap"])
    all_reqs = sorted(have | set(fam.keys()) | gap)                # have/계열 커버/gap 세 곳에 나온 역량 전부
    return [f"{skill}({'X' if skill in gap else 'O'})" for skill in all_reqs]


def _job_lines(j: dict, indent: str) -> list[str]:
    """직무 한 건의 충족/계열/태도/공고 줄. [직무](1위)와 [다음 후보]가 같은 형식을 쓴다 (9/16 팀 요청).

    9/17: 웹 <pre> 폭(LINE_WIDTH)을 넘는 줄은 항목 경계로만 나눈다(_wrap_items). "(✓ = 너의 강점 성향과 맞음)" 범례는
    여기서 빼고 render() 가 카드 끝에 한 번만 단다.
    """
    fam = j.get("family", {})
    L: list[str] = [f"{indent}요구 역량 {j['covered_count']}/{j['total']} 충족"]
    items = _job_status_items(j)
    if items:
        L += _wrap_items("", items, indent)
    by_parent: dict[str, list[str]] = {}                               # 계열 커버 — IS_A 한 홉, 상위 개념별로 묶는다
    for child, parent in sorted(fam.items()):
        by_parent.setdefault(parent, []).append(child)
    for parent, children in by_parent.items():
        L += _wrap_items(f"≈ {parent} 계열로 커버 — ", children, indent)
    soft = [f"{sk} ✓" if sk in j.get("soft_match", []) else sk for sk in j.get("soft_wanted", [])]
    if soft:                                                               # 직무가 요구하는 태도 — 데이터가 있을 때만
        L += _wrap_items("요구 태도: ", soft, indent, sep=" · ")
    if j.get("url"):
        L.append(f"{indent}공고 → {j['url']}")                              # ③ 출처 — 챗봇이 줄 수 없는 것
    return L


def _student_links(r: dict) -> tuple[list[str], dict[str, str]]:
    """학생 태그(근거 + 성향 추정)가 1위 전공에 이어진 방식 — (정확 일치 목록, {태그: 커버한 전공 역량})."""
    m = r["major"]
    return list(m.get("matched_skills", [])), dict(m.get("family", {}))


def _unlinked(r: dict) -> list[str]:
    """1위 전공에 정확·계열 어느 쪽으로도 이어지지 않은 학생 태그 (입력 순서 유지)."""
    exact, fam = _student_links(r)
    tags = list(r["tags"]) + sorted(set(r.get("inferred_tags", [])))
    return list(dict.fromkeys(t for t in tags if t not in set(exact) and t not in fam))


def _ranking_lines(rows: list[dict], indent: str) -> list[str]:
    """역량 연결도 — `█████░░░░░  65%  경영학과`. 바를 이름 **앞**에 둔다.

    이름 뒤에 두면 이름 폭만큼 채워야 바가 맞는데(_pad), 웹 폰트는 한글이 정확히 2칸이 아니라 1~2칸씩 어긋났다
    (설명서 10장 한계 11). 바가 먼저 오면 이름 길이와 무관하게 세로선이 맞는다 — 구조로 푼 것.
    """
    out = []
    for x in rows:
        raw = f"  ({x['score']:.3f})" if DEBUG else ""
        out.append(f"{indent}  {_bar(x['score'])} {_pct(x['score']):>3}%  {_pretty(x['name'])}{raw}")
    return out


def render(r: dict) -> str:
    if r.get("empty"):
        return "이야기에서 이어질 역량을 아직 찾지 못했어. 좋아하는 과목이나 직접 해 본 활동을 조금 더 알려줄래?"

    IND = " " * 10
    profile = " · ".join(r["tags"])
    if r.get("inferred_tags"):                                             # 성향에서 추정한 태그는 근거 태그와 구분해 보여준다
        profile += "   (성향에서 추정: " + " · ".join(r["inferred_tags"]) + ")"
    L = [f"[프로필]  {profile}", ""]

    # ── [전공]  ① 전수 순위 + 학생 태그가 어떻게 이어졌는지 (✓ 정확 / ≈ 계열 / ○ 미연결) + 역량 연결도 바
    m, rk = r["major"], r["ranking"]
    major_disp = _pretty(m["name"]) if _one_school(r) else f"{m['school']} {_pretty(m['name'])}"
    L.append(f"[전공]    {major_disp}")
    L.append(f"{IND}선택 이유: 전체 {r['total_majors']}개 전공 중 보유 역량과 관련된 {len(rk)}개 전공을 선정했고, "
             f"그 중 1위가 {major_disp}")
    matched, fam = _student_links(r)                                       # fam = {학생 태그: 그것을 커버한 전공 역량}
    ev = m.get("evidence", {})
    if matched:
        L += _wrap_items("✓ ", [f"{s} (과목 {len(ev.get(s, []))}개)" for s in matched], IND, sep=" · ")
    for tag, parent in sorted(fam.items()):
        L.append(f"{IND}≈ {tag} → {parent} 계열로 커버 (과목 {len(ev.get(parent, []))}개)")
    inferred = set(r.get("inferred_tags", []))
    missing = _unlinked(r)
    if missing:
        L += _wrap_items("○ 아직 안 이어진 역량 — ", [f"{t} (추정)" if t in inferred else t for t in missing], IND)
    L.append(f"{IND}역량 연결도")
    L += _ranking_lines(rk[:3], IND)
    L.append("")

    # ── [과목]  다리 과목. 과목별 꼬리표는 빼고 출처는 카드 끝 한 줄로 (9/16)
    L.append(f"[과목]    {_pretty(m['name'])}에서 이 역량을 기르는 과목")
    for s in r["subjects"]:
        L.append(f"{IND}{s['subject']} → {', '.join(s['for'])} 역량 향상")
    L.append("")

    # ── [직무]  1위 상세 + ② 갭 + 공고 URL
    j = r["job"]
    if j:
        L.append(f"[직무]    {j['company']} {j['role']} ({j['career_type']})")
        L += _job_lines(j, IND)
        # ── [다음 후보]  2·3위 — [직무]와 같은 줄 형식 (9/16). 신입 공고가 적어 1위가 몰리기 쉬운 것도 이유
        alts = r.get("jobs", [])[1:3]
        if alts:
            L.append("")
            L.append("[다음 후보]")
            for alt in alts:
                L.append(f"{IND}{alt['company']} {alt['role']} ({alt['career_type']})")
                L += _job_lines(alt, IND)

    # ── 범례 — 요구 태도의 ✓ 가 한 번이라도 떴을 때만, 카드 끝에 한 줄 (9/16 웹 피드백: 줄 끝에 붙이면 <pre> 폭을 넘는다)
    if any(x.get("soft_match") for x in r.get("jobs", [])[:3]):
        L += ["", f"{IND}(요구 태도의 ✓ = 너의 강점 성향과 맞음)"]

    # ── 출처 한 줄 — "과목명이 실존한다"(확인 항목 ②) 와 "왜 서울대만?" 의 근거. 과목명은 넣지 않는다 (확인 ② 가 누출로 잡는다)
    schools = " · ".join(sorted({x["school"] for x in rk}))
    L += ["", "─" * 10,
          f"출처 · 과목: {schools} 교육과정 — 대학알리미 {SOURCE_URLS['curriculum']} · 공고: LG Careers {SOURCE_URLS['jobs']} (스냅샷)"]
    return "\n".join(L)


# ═════════════════════════════════════════════════════════════
# 역방향 질의 — "이 직무에 가려면 어느 전공?" (9/17). LLM 0회, 그래프만 탄다 (설명서 10장 '여유 시').
#   정방향: 학생 태그 → 전공 → (전공 역량 전체) → 직무.  역방향: 직무 요구 역량 → 전공 → 그 전공의 다리 과목.
#   같은 REQUIRES/DEVELOPS 엣지를 반대로 순회할 뿐이라 graph_store 함수 하나(find_majors_for_job)로 끝난다.
# ═════════════════════════════════════════════════════════════

def reverse(query: str) -> dict:
    """직무 검색어 → {"job", "candidates", "ranking", "subjects", "total_majors"}. 못 찾으면 {"job": None}.

    같은 이름이 여러 건이면 신입 → 회사명 순으로 첫 번째를 쓰고 나머지는 candidates 로 돌려준다
    (회사명을 검색어에 같이 쓰면 좁혀진다: --job "LG CNS AI").
    """
    hits = find_jobs_by_name(query)
    if not hits:
        return {"job": None, "candidates": []}
    job = hits[0]
    ranking = find_majors_for_job(job, limit=100)
    subjects = []
    if ranking:
        top = ranking[0]
        bridge = sorted(set(top["matched_skills"]) | set(top["family"].values()))   # 정확 일치 + 계열 커버에 쓰인 전공 역량
        subjects = subjects_for(top["id"], bridge, k=3)
    return {"job": job, "candidates": hits[1:], "ranking": ranking, "subjects": subjects, "total_majors": count_majors()}


def render_reverse(rv: dict) -> str:
    IND = " " * 10
    j = rv["job"]
    if j is None:
        return "그 이름의 직무 공고를 찾지 못했어. 직무명 일부(예: Smart Factory, AI, 소재개발)나 '회사 직무명'으로 다시 찾아볼래?"
    L = [f"[직무]    {j['company']} {j['role']} ({j['career_type']})"]
    if j["requires"]:
        L += _wrap_items(f"필수 역량 {len(j['requires'])}개 — ", list(j["requires"]), IND)
    if j["prefers"]:
        L += _wrap_items(f"우대 역량 {len(j['prefers'])}개 — ", list(j["prefers"]), IND)
    if not j["requires"] and not j["prefers"]:
        L.append(f"{IND}공고에 역량 문장이 없어 전공을 이을 수 없어")
    if j.get("url"):
        L.append(f"{IND}공고 → {j['url']}")
    if rv["candidates"]:
        L.append(f"{IND}같은 이름 {len(rv['candidates'])}건 더 — "
                 + " · ".join(f"{c['company']} {c['role']} ({c['career_type']})" for c in rv["candidates"][:4]))
    L.append("")

    rk = rv["ranking"]
    if not rk:
        L.append("[전공]    이 역량을 기르는 전공을 찾지 못했어")
        return "\n".join(L)
    one_school = len({m["school"] for m in rk}) == 1
    L.append(f"[전공]    이 직무의 역량을 기르는 전공 — {rv['total_majors']}개 중 이어지는 {len(rk)}개를 비교")
    L.append(f"{IND}역량 연결도 (필수 1.0 · 우대 0.5 가중)")
    L += _ranking_lines(rk[:3], IND)
    for x in rk[:3]:                                                       # 전공마다 무엇이 정확(✓)·계열(≈)로 이어졌나
        L.append(f"{IND}{_pretty(x['name']) if one_school else x['school'] + ' ' + _pretty(x['name'])}")
        if x["matched_skills"]:
            L += _wrap_items("✓ ", x["matched_skills"], IND + "  ")
        if x["family"]:
            L += _wrap_items("≈ ", [f"{c}→{p}" for c, p in sorted(x["family"].items())], IND + "  ")
    L.append("")

    top = rk[0]
    L.append(f"[과목]    {_pretty(top['name'])}에서 이 역량을 기르는 과목")
    for sub in rv["subjects"]:
        L.append(f"{IND}{sub['subject']} → {', '.join(sub['for'])}")

    schools = " · ".join(sorted({x["school"] for x in rk}))
    L += ["", "─" * 10,
          f"출처 · 과목: {schools} 교육과정 — 대학알리미 {SOURCE_URLS['curriculum']} · 공고: LG Careers {SOURCE_URLS['jobs']} (스냅샷)"]
    return "\n".join(L)


EXPLAIN_SYSTEM = """너는 고등학생 진로 상담 전문가다.
아래 [근거]에 주어진 사실만 사용해서, 학생에게 보여줄 "진로 추천" 문단을 작성하라.
이 문단은 화면 위쪽의 추천 카드(전공 순위·과목·직무 요구 역량 커버 현황) **아래에 붙는 설명**이다.
숫자와 근거는 카드가 이미 보여주므로 다시 나열하지 말고, 카드의 항목들이 왜 그렇게 이어지는지 풀어 쓴다.
단, 1단락에는 "전공 N개를 모두 비교했고, 그중 학생의 역량과 이어지는 M개 가운데 가장 잘 이어진 전공" 이라는 취지의
문장을 **반드시 한 번** 친절한 말로 넣는다 — 숫자 N, M 은 [근거]의 "전체 전공 수 / 이어진 전공 수" 값을 그대로 쓴다.
같은 문장(또는 바로 다음 문장)에서 **왜 가장 잘 이어졌는지**를 [근거]의 "[학생 역량이 이 전공에 이어진 방식]" 항목으로
구체화한다 — 학생 역량 총 몇 개 중 몇 개가 이 전공의 과목으로 직접 이어지고, 몇 개가 계열(상위 개념)로 이어지는지.
숫자와 역량 이름은 **그 항목의 것을 그대로** 쓴다. [근거 과목과 연결 역량] 목록에 등장하는 역량 수로 세지 않는다
(그 목록은 과목 3개만 보여주므로 역량이 빠져 있을 수 있다). 미연결이 0이면 말하지 않는다.
(예: "61개 전공을 모두 살펴봤고, 네 역량과 이어지는 46개 중에서 통계학과가 가장 잘 이어졌어요. 네 역량 세 가지 중
 두 가지(데이터 분석·통계)는 통계학과 과목에서 직접 다루고, 나머지 하나(파이썬)는 프로그래밍 계열로 이어져요.")
전공명·과목명·직무명·회사명은 문장 안에 자연스럽게 포함한다.

절대 규칙:
1. [근거]에 없는 과목명, 역량명, 회사명, 직무명을 절대 지어내지 않는다.
2. 단, 주어진 과목명·역량명이 일반적으로 무엇을 다루는지 설명하는 것은 허용한다
   (예: "데이터마이닝 방법 및 실습"은 대량의 데이터에서 패턴을 찾아내는 방법을 배우는
   과목이라는 일반 상식 수준의 설명). [근거]에 없는 회사의 구체적인 프로젝트나 사실을
   지어내는 것과는 다르다 — 이건 하지 않는다.
3. 직무가 어떤 일을 하는지는 **[근거]에 적힌 요구 역량으로만** 말한다. 그 회사·직무의 실제 업무 내용은
   우리 데이터에 없으므로 상상해서 쓰지 않는다.
4. [학생 프로필]이 주어졌다면, 그 안의 관심사·성향만 언급한다. 거기 없는 성격·경험·에피소드를
   지어내지 않는다. 프로필 문장을 그대로 인용하지 말고 자연스러운 말로 풀어 쓴다.
5. 문장 수를 채우려고 내용을 늘리지 않는다. 할 말이 적으면 짧게 쓴다.

작성 순서 (3단락, gap 이 있을 때만 4단락. 각 단락 사이 줄바꿈):

[1단락 - 도입, 2~3문장]
[학생 프로필]이 주어졌다면, 그 안의 관심사·성향이 왜 이 전공과 어울리는지 짧게 엮은 다음, 전공
진학과 수강할 과목을 추천하는 문장으로 이어간다. [학생 프로필]이 없다면 전공 진학과 수강할 과목을
바로 추천하는 문장으로 시작한다.
예 (프로필이 있을 때): "수학을 잘하고 혼자 기록하며 공부하는 걸 편하게 느낀다면, 데이터를 차분히
파고드는 성향과 잘 맞습니다. 당신은 통계학과에 진학하여 '데이터마이닝 방법 및 실습',
'실험계획 및 실습', '함수추정의 응용 및 실습' 과목들을 듣는 것을 추천합니다."
예 (프로필이 없을 때): "당신은 통계학과에 진학하여 '데이터마이닝 방법 및 실습', '실험계획
및 실습', '함수추정의 응용 및 실습' 과목들을 듣는 것을 추천합니다."

[2단락 - 과목이 역량을 기르는 이유, 2~3문장]
[근거]의 과목들이 왜, 어떻게 해당 역량(Skill)을 길러주는지 고등학생도 이해할 수 있는
쉬운 말로 설명한다. 각 과목이 다루는 일반적인 내용을 하나씩 짚는다.

[3단락 - 역량이 직무에 필요한 이유, 2~3문장]
[근거]의 "직무 요구 중 전공이 커버하는 역량"과 "상위 개념으로 커버하는 역량"을 근거로,
그 전공에서 기른 역량이 직무의 어떤 요구와 이어지는지 설명한다. (직무의 실제 업무는 서술하지 않는다 — 규칙 3)

[4단락 - 부족한 역량, [근거]에 "[직무가 요구하지만 전공에 없는 역량(gap)]" 항목이 **있을 때만** 1~2문장]
"다만 ~도 직무에서 요구되는 핵심 역량인데, 전공 과목에서 다루어지지 않으므로 교과 밖에서
별도로 학습해야 한다"처럼 언급한다.
[근거]에 그 항목이 없으면 4단락은 **쓰지 않는다** — 3단락에서 글을 끝낸다. "부족한 역량이 없다",
"다행히", "추가 학습이 필요하지 않다", "모두 갖추고 있다" 같은 문장도 쓰지 않는다 (없는 것을 언급하는 것
자체가 4단락이다).

전체적으로 확신에 찬 어조보다는 신중하고 친절한 설명 어조를 유지한다."""

def build_explain_prompt(r: dict) -> str:
    """run()의 결과 dict에서 근거만 뽑아 프롬프트 텍스트로 만든다.
    graph_store가 실제로 돌려준 값(major/job/subjects)만 사용 — 지어낼 재료를 주지 않는다."""
    major = r["major"]
    job = r["job"]
    subjects = r["subjects"]

    # subjects_for() 는 {"subject": 과목명, "hits": n, "for": [역량...]} 딕셔너리를 돌려준다.
    # "for" 에 이미 "어느 역량의 근거였는지" 가 들어 있으므로 그대로 쓴다.
    # (이전 코드는 딕셔너리를 문자열처럼 `subj in via` 로 비교해 항상 False 였고, 프롬프트에 딕셔너리가 통째로 찍혔다)
    subject_lines = [f"- {s['subject']} → {', '.join(s['for']) or '(연결된 역량 없음)'}" for s in subjects]

    fam = job.get("family", {}) if job else {}
    family_text = ", ".join(f"{child} (전공의 {parent} 로 커버)" for child, parent in sorted(fam.items())) or "(없음)"

    lines: list[str] = []
    if r.get("profile_summary"):                     # 대화(또는 JSON)로 얻은 학생 프로필 — 있을 때만 1단락에 쓰인다
        lines += ["[학생 프로필]", r["profile_summary"], ""]

    # 학생 역량 → 1위 전공 연결 상태. render() 의 ✓/≈/○ 와 같은 계산 — 1단락 "왜 가장 잘 이어졌는지" 의 재료 (9/16 웹 피드백)
    exact, fam_m = _student_links(r)
    link_parts = [f"과목으로 직접 {len(exact)}개" + (f" ({', '.join(exact)})" if exact else ""),
                  f"계열로 {len(fam_m)}개" + (f" ({', '.join(f'{t} → {p}' for t, p in sorted(fam_m.items()))})" if fam_m else "")]
    missing = _unlinked(r)
    if missing:
        link_parts.append(f"미연결 {len(missing)}개 ({', '.join(missing)})")

    lines += [
        f"전공: {major['name'] if _one_school(r) else major['school'] + ' ' + major['name']}",
        f"전체 전공 수 / 이어진 전공 수: {r.get('total_majors', '?')} / {len(r.get('ranking', []))}",   # 1단락 '전수 비교' 한 문장의 재료
        f"직무: {job['company']} {job['role']} ({job['career_type']})" if job else "직무: (매칭 없음)",
        "",
        "[학생 역량이 이 전공에 이어진 방식 — 1단락의 '몇 개 중 몇 개' 는 이 숫자만 쓴다]",
        f"학생 역량 총 {len(exact) + len(fam_m) + len(missing)}개 · " + " · ".join(link_parts),
        "",
        "[근거 과목과 연결 역량]",
        *subject_lines,
        "",
        f"[직무 요구 중 전공이 정확히 커버하는 역량]\n{', '.join(job['have']) if job and job['have'] else '(없음)'}",
        f"[직무 요구 중 상위 개념으로 커버하는 역량 — IS_A 한 홉]\n{family_text}",
    ]
    if job and job["gap"]:                                   # gap 이 없으면 항목 자체를 주지 않는다 — "(없음)" 을 주면 모델이 "다행히 …" 로 언급한다 (한계 12)
        lines.append(f"[직무가 요구하지만 전공에 없는 역량(gap)]\n{', '.join(job['gap'])}")
    return "\n".join(lines)

def _build_explain_chain():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=20, max_retries=2)
    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPLAIN_SYSTEM),
        ("human", "{evidence}"),
    ])
    return prompt | llm


def explain_stream(r: dict):
    """진로 추천 문단을 청크(str) 단위로 yield — 동기. 웹 화면의 SSE 스트리밍용.

    run() 결과에 major/job이 없으면 아무것도 내보내지 않는다.
    """
    if not r.get("major") or not r.get("job"):
        return
    chain = _build_explain_chain()
    for chunk in chain.stream({"evidence": build_explain_prompt(r)}):
        yield chunk.content


async def explain(r: dict) -> None:
    """진로 추천 문단을 스트리밍으로 출력. run() 결과에 major/job/subjects가 있을 때만 호출."""
    if not r.get("major") or not r.get("job"):
        return

    chain = _build_explain_chain()

    print("[진로 추천] ", end="", flush=True)
    async for chunk in chain.astream({"evidence": build_explain_prompt(r)}):
        print(chunk.content, end="", flush=True)
    print()

# 화면 = 추천 카드(render) + 설명 문단(explain). 카드가 근거(순위·커버리지·출처)이고 문단은 그 풀이다 — 둘 다 사용자에게 보인다.
#   설계서 2절: "우리의 차이(실제 데이터·재현성·출처)는 화면에 드러내지 않으면 보이지 않는다".
# DEBUG=1 (환경변수) 이면 상위 순위 내부값(점수·근거 수)을 추가로 찍는다 — 팀 내부 확인용.
DEBUG = os.environ.get("DEBUG", "0") == "1"
if __name__ == "__main__":
    import asyncio
    import sys

    session: dict = {}
    trait_tags: list[str] = []
    profile_summary: str | None = None

    # 네 가지 입력 방식. 프로필 기반 셋(기본값/--interview/--profile)은 interview.py 가 같은 모양
    # ({"answers", "interest_tags", "trait_tags", ...})으로 돌려주고, Q3(① ② ③)는 더 이상 따로 묻지 않는다 —
    # interview.infer_orientation() 이 이미 모은 프로필(강점·공부 스타일·친구 관계·가치관...)로 같은 판단을
    # 대신한다. 자연스러운 대화 중간에 객관식이 끼어드는 게 어색하다는 이유로 뺐다 (2026-09-16).
    #   (플래그 없음)        : 기본값. user_analysis/main.py 와 완전히 같은 흐름 (7개 영역, 적응형 질문)
    #   --profile <path>   : main.py 가 저장한 JSON을 그대로 읽는다 (대화 없음)
    #   --interview        : 데모용 축약 버전 (2개 영역, 고정 질문 최대 1회)
    #   --basic            : 원래의 고정 3질문 모드 (user_analysis 연동 이전 방식) — Q3 를 그대로 묻는다
    #   --job <직무명>     : 역방향 — "이 직무에 가려면 어느 전공?" LLM 0회 (9/17)
    if "--job" in sys.argv:
        query = " ".join(sys.argv[sys.argv.index("--job") + 1:]) or input("\n어떤 직무가 궁금해? (직무명 일부)\n> ")
        print("\n" + render_reverse(reverse(query)))
        sys.exit(0)

    if "--profile" in sys.argv:
        from interview import from_profile_file
        path = sys.argv[sys.argv.index("--profile") + 1]
        iv = from_profile_file(path)
        print(f"\n({path} 의 프로필을 읽었습니다)")
    elif "--interview" in sys.argv:
        from interview import interview
        iv = interview()
    elif "--basic" in sys.argv:
        iv = None
    else:
        from interview import full_interview
        iv = full_interview()

    if iv is not None:
        # normalize_to_tags()/webapp.py/check.py 는 answers[2] 자리를 "Q3"로 취급해 자유 태거 입력에서 뺀다
        # (규칙 기반으로 따로 처리하려고). Q3 를 안 묻는 모드에서도 그 계약은 그대로 두고, 빈 문자열로
        # 자리만 맡아 둔다 — 그래야 재질문 답이 answers[3]에 붙어서 자유 태거 입력에 제대로 들어간다.
        answers = iv["answers"] + [""]
        trait_tags, stated_tags, soft_traits = iv["trait_tags"], iv["interest_tags"], iv["soft_traits"]
        profile_summary = iv.get("profile_summary")
        if iv["interest_evidence"]:
            # 성향 판단(예전 Q3)도 interview.py 에서 interest_evidence 에 같이 얹혀 오므로 여기 한 줄로 같이 보인다
            print("\n(관심·성향에서 읽은 역량: " + "; ".join(f"{s} ← {e}" for s, e in iv["interest_evidence"].items()) + ")")
        if iv["trait_evidence"]:
            print("(강점 성향에서 추정한 역량: " + "; ".join(f"{s} ← {e}" for s, e in iv["trait_evidence"].items()) + ")")
    else:
        answers = [input(f"\n{q}\n> ") for q in QUESTIONS]
        stated_tags, soft_traits = [], []

    kw = dict(trait_tags=trait_tags, stated_tags=stated_tags, soft_traits=soft_traits, profile_summary=profile_summary)
    result = run(answers, session, **kw)
    if "followup" in result:
        answers.append(input(f"\n{FOLLOWUP_PREFIX}{result['followup']}\n> "))
        result = run(answers, session, **kw)

    if result.get("empty"):
        print("\n추천할 만한 전공을 찾지 못했습니다. 다른 관심사로 다시 시도해보세요.")
    else:
        print("\n" + render(result))                      # ① 추천 카드 — 근거 (항상 보인다)
        if DEBUG:                                          # 내부 확인: 상위 5개 점수·근거 수
            print("\n[DEBUG 순위]", [(x["name"], round(x["score"], 2), x["evidence_count"]) for x in result["ranking"][:5]])
        if result.get("major") and result.get("job"):
            asyncio.run(explain(result))                   # ② 설명 문단 — 카드의 풀이