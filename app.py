"""app.py — 온라인 파이프라인 (담당: D)"""
from __future__ import annotations

import json
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from vocab import CANON
from graph_store import (find_majors_by_skills, find_jobs_by_skills,
                         subjects_for, count_majors, taggable_skills)

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


def run(answers: list[str], session: dict, trait_tags: list[str] | None = None) -> dict:
    """answers: [Q1, Q2, Q3(, 재질문 답)].  trait_tags: 인터뷰 모드에서 성향→역량으로 추정한 태그 (선택)."""
    tags = normalize_to_tags(answers)

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
    jobs = find_jobs_by_skills(major_skills, limit=2, career_type="신입")   # 정의: 신입 직무 추천
    if not jobs:                                                            # 신입 공고와 안 이어지면 전체에서
        jobs = find_jobs_by_skills(major_skills, limit=2)
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
            "major": major, "job": job, "jobs": jobs, "subjects": subjects}


def render(r: dict) -> str:
    if r.get("empty"):
        return "입력하신 내용으로는 IT 역량이 검출되지 않았습니다. 다시 답해 보시겠어요?"

    profile = " · ".join(r["tags"])
    if r.get("inferred_tags"):                                             # 성향에서 추정한 태그는 근거 태그와 구분해 보여준다
        profile += "   (성향에서 추정: " + " · ".join(r["inferred_tags"]) + ")"
    L = [f"[프로필]  {profile}", ""]

    m, rk = r["major"], r["ranking"]
    L.append(f"[전공]    {m['school']} {m['name']}")
    L.append(f"          {r['total_majors']}개 전공 중 IT 역량이 검출된 "
             f"{len(rk)}개를 비교한 결과 1위")                       # ① 전수 순위
    L.append("          " + " / ".join(f"{x['score']:.2f} {x['name']}" for x in rk[:3]))
    L.append("")

    L.append("[과목]")
    for s in r["subjects"]:
        L.append(f"          {s['subject']} → {', '.join(s['for'])}  [{m['school']} 개설]")  # ③ 출처 — 데이터에서, 하드코딩 금지
    L.append("")

    j = r["job"]
    if j:
        L.append(f"[직무]    {j['company']} {j['role']} ({j['career_type']})")
        fam = j.get("family", {})
        L.append(f"          요구 역량 {j['total']}개 중 {j['covered_count']}개 커버"
                 + (f" (정확 {len(j['have'])} · 계열 {len(fam)})" if fam else ""))
        if j["have"]:
            L.append(f"          ✓ {', '.join(j['have'])}")
        if fam:                                                                # 계열 커버 — IS_A 한 홉
            by_parent: dict[str, list[str]] = {}                               # 상위 개념별로 묶어서 보여준다
            for child, parent in sorted(fam.items()):
                by_parent.setdefault(parent, []).append(child)
            for parent, children in by_parent.items():
                L.append(f"          ≈ {parent} 계열로 커버 — {', '.join(children)}")
        if j["gap"]:
            L.append(f"          ✗ 교과 밖에서 채울 것 — {', '.join(j['gap'])}")   # ② 갭
        # 2위 직무 한 줄 — 신입 공고가 적어(23개) 1위가 몰리기 쉬우므로 다음 후보를 같이 보여준다
        for alt in r.get("jobs", [])[1:2]:
            L.append(f"          다음 후보: {alt['company']} {alt['role']} ({alt['career_type']}) — "
                     f"요구 {alt['total']}개 중 {alt['covered_count']}개 커버")
    return "\n".join(L)

EXPLAIN_SYSTEM = """너는 고등학생 진로 상담 전문가다.
아래 [근거]에 주어진 사실만 사용해서, 학생에게 보여줄 "진로 추천" 문단을 작성하라.
이 문단은 화면 위쪽의 추천 카드(전공 순위·과목·직무 요구 역량 커버 현황) **아래에 붙는 설명**이다.
숫자와 근거는 카드가 이미 보여주므로 다시 나열하지 말고, 카드의 항목들이 왜 그렇게 이어지는지 풀어 쓴다.
전공명·과목명·직무명·회사명은 문장 안에 자연스럽게 포함한다.

절대 규칙:
1. [근거]에 없는 과목명, 역량명, 회사명, 직무명을 절대 지어내지 않는다.
2. 단, 주어진 과목명·역량명이 일반적으로 무엇을 다루는지 설명하는 것은 허용한다
   (예: "데이터마이닝 방법 및 실습"은 대량의 데이터에서 패턴을 찾아내는 방법을 배우는
   과목이라는 일반 상식 수준의 설명). [근거]에 없는 회사의 구체적인 프로젝트나 사실을
   지어내는 것과는 다르다 — 이건 하지 않는다.
3. 직무가 어떤 일을 하는지는 **[근거]에 적힌 요구 역량으로만** 말한다. 그 회사·직무의 실제 업무 내용은
   우리 데이터에 없으므로 상상해서 쓰지 않는다.
4. 문장 수를 채우려고 내용을 늘리지 않는다. 할 말이 적으면 짧게 쓴다.

작성 순서 (총 4단락, 각 단락 사이 줄바꿈):

[1단락 - 도입, 1~2문장]
전공 진학과 수강할 과목을 직접 추천하는 문장으로 시작한다.
예: "당신은 서울대학교 통계학과에 진학하여 '데이터마이닝 방법 및 실습', '실험계획 및 실습',
'함수추정의 응용 및 실습' 과목들을 듣는 것을 추천합니다."

[2단락 - 과목이 역량을 기르는 이유, 2~3문장]
[근거]의 과목들이 왜, 어떻게 해당 역량(Skill)을 길러주는지 고등학생도 이해할 수 있는
쉬운 말로 설명한다. 각 과목이 다루는 일반적인 내용을 하나씩 짚는다.

[3단락 - 역량이 직무에 필요한 이유, 2~3문장]
[근거]의 "직무 요구 중 전공이 커버하는 역량"과 "상위 개념으로 커버하는 역량"을 근거로,
그 전공에서 기른 역량이 직무의 어떤 요구와 이어지는지 설명한다. (직무의 실제 업무는 서술하지 않는다 — 규칙 3)

[4단락 - 부족한 역량, 있을 때만 1~2문장]
gap(부족한 역량)이 있다면 "다만 ~도 직무에서 요구되는 핵심 역량인데, 전공 과목에서
다루어지지 않으므로 교과 밖에서 별도로 학습해야 한다"처럼 언급한다. gap이 없으면 이
단락은 생략한다.

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

    lines = [
        f"전공: {major['school']} {major['name']}",
        f"직무: {job['company']} {job['role']} ({job['career_type']})" if job else "직무: (매칭 없음)",
        "",
        "[근거 과목과 연결 역량]",
        *subject_lines,
        "",
        f"[직무 요구 중 전공이 정확히 커버하는 역량]\n{', '.join(job['have']) if job and job['have'] else '(없음)'}",
        f"[직무 요구 중 상위 개념으로 커버하는 역량 — IS_A 한 홉]\n{family_text}",
        f"[직무가 요구하지만 전공에 없는 역량(gap)]\n{', '.join(job['gap']) if job and job['gap'] else '(없음)'}",
    ]
    return "\n".join(lines)

async def explain(r: dict) -> None:
    """진로 추천 문단을 스트리밍으로 출력. run() 결과에 major/job/subjects가 있을 때만 호출."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    if not r.get("major") or not r.get("job"):
        return

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=20, max_retries=2)
    prompt = ChatPromptTemplate.from_messages([
        ("system", EXPLAIN_SYSTEM),
        ("human", "{evidence}"),
    ])
    chain = prompt | llm

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

    if "--interview" in sys.argv:
        # 대화형 모드: 자기소개 → 부족한 영역만 질문 (user_analysis 어댑터). Q3 는 그대로 묻는다
        from interview import interview
        iv = interview()
        q3 = input(f"\n{QUESTIONS[2]}\n> ")
        answers = iv["answers"] + [q3]
        trait_tags = iv["trait_tags"]
        if iv["trait_evidence"]:
            print("\n(성향에서 추정한 역량: " + "; ".join(f"{s} ← {e}" for s, e in iv["trait_evidence"].items()) + ")")
    else:
        answers = [input(f"\n{q}\n> ") for q in QUESTIONS]

    result = run(answers, session, trait_tags=trait_tags)
    if "followup" in result:
        answers.append(input(f"\n{FOLLOWUP_PREFIX}{result['followup']}\n> "))
        result = run(answers, session, trait_tags=trait_tags)

    if result.get("empty"):
        print("\n추천할 만한 전공을 찾지 못했습니다. 다른 관심사로 다시 시도해보세요.")
    else:
        print("\n" + render(result))                      # ① 추천 카드 — 근거 (항상 보인다)
        if DEBUG:                                          # 내부 확인: 상위 5개 점수·근거 수
            print("\n[DEBUG 순위]", [(x["name"], round(x["score"], 2), x["evidence_count"]) for x in result["ranking"][:5]])
        if result.get("major") and result.get("job"):
            asyncio.run(explain(result))                   # ② 설명 문단 — 카드의 풀이