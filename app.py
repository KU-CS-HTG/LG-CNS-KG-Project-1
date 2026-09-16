"""app.py — 온라인 파이프라인 (담당: D)"""
from __future__ import annotations

import json
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from graph_store import (find_majors_by_skills, find_jobs_by_skills,
                         subjects_for, count_majors, all_skills)

load_dotenv()

QUESTIONS = [
    "관심 있는 분야나 하고 싶은 일을 자유롭게 적어주세요.",
    "스스로 잘한다고 생각하는 것은 무엇인가요?",
    "다음 중 더 끌리는 쪽은? ① 데이터를 파고들어 패턴 찾기 "
    "② 시스템을 설계하고 만들기 ③ 사람과 일정을 조율해 프로젝트 굴리기",
]
# 태그 목록은 사전(CANON) 전체가 아니라 **그래프에 실제로 있는 역량**만.
#   사전에는 있지만 그래프엔 없는 역량(Problem Solving, Communication, Knowledge Graph — 전공 쪽 제외)이 태그가 되면
#   어느 전공과도 안 맞으면서 커버리지 분모만 키운다. 실측(9/15): 3태그 중 1개가 그런 태그라 상위권이 전부 0.82 동점.
TAGS: list[str] = sorted(all_skills())

class Tags(BaseModel):
    tags: list[str]

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_TAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "사용자 답변에서 역량 태그를 뽑습니다.\n"
     "반드시 다음 목록에 있는 태그만 사용하세요: {tag_list}\n"
     "목록에 없는 말은 만들지 마세요. 최대 5개."),
    ("human", "{answers}"),
])
_tagger = _TAG_PROMPT | _llm.with_structured_output(Tags)


def normalize_to_tags(answers: list[str]) -> list[str]:
    """답변 → 통제 어휘 태그. 목록 밖 태그는 2중으로 걸러낸다."""
    res = _tagger.invoke({"tag_list": ", ".join(TAGS),
                          "answers": "\n".join(answers)})
    return [t for t in res.tags if t in set(TAGS)]


def run(answers: list[str], session: dict) -> dict:
    tags = normalize_to_tags(answers)

    if len(tags) < 2 and not session.get("asked_again"):     # 조건부 분기, 1회
        session["asked_again"] = True
        return {"followup": QUESTIONS[0]}

    session["tags"] = list(dict.fromkeys(session.get("tags", []) + tags))
    tags = session["tags"]

    # ① 전공 — limit을 크게 줘서 순위를 전부 받는다
    ranking = find_majors_by_skills(tags, limit=100)
    if not ranking:
        return {"tags": tags, "empty": True}
    major = ranking[0]

    # ② 직무 — 사용자 태그가 아니라 '전공이 기르는 역량'으로 찾는다 ★
    major_skills = list(major["evidence"].keys())
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

    return {"tags": tags, "ranking": ranking, "total_majors": count_majors(),
            "major": major, "job": job, "subjects": subjects}


def render(r: dict) -> str:
    if r.get("empty"):
        return "입력하신 내용으로는 IT 역량이 검출되지 않았습니다. 다시 답해 보시겠어요?"

    L = [f"[프로필]  {' · '.join(r['tags'])}", ""]

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
    return "\n".join(L)

EXPLAIN_SYSTEM = """너는 대학생 진로 상담 전문가다.
아래 [근거]에 주어진 사실만 사용해서, 학생에게 보여줄 "진로 추천" 문단을 작성하라.
이 문단이 사용자가 보는 전부이므로, 전공명·과목명·직무명·회사명을 문장 안에 자연스럽게 모두 포함해야 한다.

절대 규칙:
1. [근거]에 없는 과목명, 역량명, 회사명, 직무명을 절대 지어내지 않는다.
2. 단, 주어진 과목명·역량명이 일반적으로 무엇을 다루는지 설명하는 것은 허용한다
   (예: "데이터마이닝 방법 및 실습"은 대량의 데이터에서 패턴을 찾아내는 방법을 배우는
   과목이라는 일반 상식 수준의 설명). [근거]에 없는 회사의 구체적인 프로젝트나 사실을
   지어내는 것과는 다르다 — 이건 하지 않는다.

작성 순서 (총 4단락, 각 단락 사이 줄바꿈):

[1단락 - 도입, 1~2문장]
전공 진학과 수강할 과목을 직접 추천하는 문장으로 시작한다.
예: "당신은 서울대학교 통계학과에 진학하여 '데이터마이닝 방법 및 실습', '실험계획 및 실습',
'함수추정의 응용 및 실습' 과목들을 듣는 것을 추천합니다."

[2단락 - 과목이 역량을 기르는 이유, 반드시 3문장 이상]
[근거]의 과목들이 왜, 어떻게 해당 역량(Skill)을 길러주는지 고등학생도 이해할 수 있는
쉬운 말로 구체적으로 설명한다. 각 과목이 다루는 일반적인 내용을 하나씩 짚어가며 설명한다.

[3단락 - 역량이 직무에 필요한 이유, 반드시 3문장 이상]
그 역량이 왜 해당 회사·직무에서 실제로 필요한지, 그 직무가 어떤 일을 하는 자리인지
일반적인 상식 수준에서 구체적으로 설명한다.

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

    # 과목별로 "어느 역량의 근거였는지"를 같이 적어준다 (evidence 딕셔너리 역참조)
    subject_lines = []
    for subj in subjects:
        matched_skills = [
            skill for skill, via in major["evidence"].items() if subj in via
        ]
        subject_lines.append(f"- {subj} → {', '.join(matched_skills) or '(연결된 역량 없음)'}")

    lines = [
        f"전공: {major['school']} {major['name']}",
        f"직무: {job['company']} {job['role']} ({job['career_type']})" if job else "직무: (매칭 없음)",
        "",
        "[근거 과목과 연결 역량]",
        *subject_lines,
        "",
        f"[직무가 갖춘 역량(have)]\n{', '.join(job['have']) if job else '(없음)'}",
        f"[직무가 요구하지만 전공에 없는 역량(gap)]\n{', '.join(job['gap']) if job and job['gap'] else '(없음)'}",
    ]
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

DEBUG = 1  #0이면 사용자가 보는 화면대로만 출력, 1이면 세부사항 전부 출력
if __name__ == "__main__":
    import asyncio
    import os

    session: dict = {}
    answers = [input(f"\n{q}\n> ") for q in QUESTIONS]
    result = run(answers, session)
    if "followup" in result:
        answers.append(input(f"\n조금 더 알려주세요. {result['followup']}\n> "))
        result = run(answers, session)

    # 팀 내부 디버그용 — 실제 서비스 화면엔 노출하지 않는다.
    # 환경변수 DEBUG=1일 때만 개발자가 확인할 수 있도록 분리.
    if DEBUG:
        print("\n[내부 디버그]\n" + render(result))

    if result.get("major") and result.get("job"):
        asyncio.run(explain(result))
    elif result.get("empty"):
        print("추천할 만한 전공을 찾지 못했습니다. 다른 관심사로 다시 시도해보세요.")