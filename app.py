"""app.py — 온라인 파이프라인 (담당: D)"""
from __future__ import annotations

import json
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from vocab import CANON
from graph_store import (find_majors_by_skills, find_jobs_by_skills,
                         subjects_for, count_majors)

load_dotenv()

QUESTIONS = [
    "관심 있는 분야나 하고 싶은 일을 자유롭게 적어주세요.",
    "스스로 잘한다고 생각하는 것은 무엇인가요?",
    "다음 중 더 끌리는 쪽은? ① 데이터를 파고들어 패턴 찾기 "
    "② 시스템을 설계하고 만들기 ③ 사람과 일정을 조율해 프로젝트 굴리기",
]
TAGS: list[str] = sorted(set(CANON.values()))

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

    # ③ 다리 과목 — 직무가 요구하고 전공도 가진 역량 기준
    bridge = sorted(set(major_skills) & set(job["have"])) if job else major_skills
    subjects = subjects_for(major["id"], bridge, k=3)

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
        L.append(f"          {s['subject']} → {', '.join(s['for'])}  [서울대 개설]")  # ③ 출처
    L.append("")

    j = r["job"]
    if j:
        L.append(f"[직무]    {j['company']} {j['role']} ({j['career_type']})")
        L.append(f"          요구 역량 {j['total']}개 중 {j['covered_count']}개 커버")
        L.append(f"          ✓ {', '.join(j['have'])}")
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