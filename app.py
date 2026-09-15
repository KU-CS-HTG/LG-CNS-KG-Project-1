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


if __name__ == "__main__":
    session: dict = {}
    answers = [input(f"\n{q}\n> ") for q in QUESTIONS]
    result = run(answers, session)
    if "followup" in result:
        answers.append(input(f"\n조금 더 알려주세요. {result['followup']}\n> "))
        result = run(answers, session)
    print("\n" + render(result))