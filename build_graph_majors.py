"""
build_graph_majors.py — subject_cleaned.csv → graph.json 의 전공 절반 (담당: C)

설계서 2절 그대로:
  과목명만 있고 과목 설명이 없다 → 과목 단위로 뽑으면 LLM의 상식일 뿐이다.
  전공 단위로 40~60개 과목을 한 번에 보여주면 성격이 선명해진다.

호출 수: 전공 1개당 LLM 1회. 3개 대학이면 150~250회.

실행:
    python build_graph_majors.py sample     # 3~5개만 시범 추출 (월요일에 반드시 먼저)
    python build_graph_majors.py            # 전체 배치
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd                      # pandas: 표 형태 데이터를 다루는 표준 라이브러리
from pydantic import BaseModel, Field

from vocab import canonicalize

DATA = Path(__file__).resolve().parent / "data"   # 이 파일이 있는 폴더 기준 → 어디서 실행해도 같은 경로
CSV = DATA / "subject_cleaned.csv"
CACHE = DATA / "majors_extracted.json"    # 전공별 LLM 원출력. 직무 쪽 extracted_raw.json 과 같은 역할
GRAPH = DATA / "graph.json"

# 대상 대학 — 월요일에 3개로 확정 (설계서 0절)
TARGET_SCHOOLS: list[str] = []           # 빈 리스트면 전체. 확정되면 여기에 3개 적는다

MAX_SUBJECTS = 80                        # 한 전공에서 LLM에 보여줄 과목 수 상한 (토큰 방어)


# ═════════════════════════════════════════════════════════════
# LLM 출력 스키마
# ═════════════════════════════════════════════════════════════

class SkillEvidence(BaseModel):
    """역량 하나 + 그 근거가 된 과목들."""
    skill: str = Field(description="역량명. 통제 어휘 목록 안에서만 고른다")
    via: list[str] = Field(description="근거 과목명. 반드시 입력으로 준 과목 목록에 있는 것만")


class MajorSkills(BaseModel):
    skills: list[SkillEvidence] = Field(description="이 전공이 기르는 역량. 4~8개")


EXTRACT_SYSTEM = """너는 대학 교육과정을 분석해 전공이 기르는 역량을 판별하는 전문가다.

입력: 전공명 + 그 전공의 개설 과목명 목록
출력: 이 전공이 기르는 역량 4~8개. 각 역량마다 근거가 된 과목명을 함께.

[엄격한 규칙]
1. `skill` 은 아래 **통제 어휘 목록에 있는 것만** 쓴다. 목록에 없는 역량은 만들지 않는다.
2. `via` 는 **입력으로 준 과목 목록에 글자 그대로 있는 과목명만** 쓴다.
   비슷한 과목을 지어내거나 이름을 바꾸지 않는다.
3. 과목명 하나만 보고 추측하지 말고, 과목 목록 전체의 경향으로 판단한다.
4. 근거 과목이 1개뿐인 역량은 넣지 않는다. 최소 2개 과목이 뒷받침해야 한다.
5. 확신이 없으면 넣지 않는다. 4개만 나와도 된다.

[통제 어휘 목록]
{vocab_list}"""


def build_chain():
    from dotenv import load_dotenv
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from vocab import CANON

    load_dotenv()
    vocab_list = ", ".join(sorted(set(CANON.values())))

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACT_SYSTEM),
        ("human", "전공명: {major}\n\n개설 과목 ({n}개):\n{subjects}"),
    ]).partial(vocab_list=vocab_list)
    return prompt | llm.with_structured_output(MajorSkills)


def extract_skills(major: str, subjects: list[str], chain=None) -> list[dict]:
    """설계서 4절 계약 함수. 전공 1개 → [{"skill":..., "via":[...]}]"""
    chain = chain or build_chain()
    shown = subjects[:MAX_SUBJECTS]

    try:
        result = chain.invoke({
            "major": major,
            "n": len(shown),
            "subjects": "\n".join(f"- {s}" for s in shown),
        })
    except Exception as e:
        print(f"  ! 추출 실패 {major}: {e}")
        return []

    # ── 검증 2겹 (환각 검사). 순서: 검증 → 정규화
    subject_set = set(shown)
    out = []
    for item in result.skills:
        # ① via 가 실제 과목인가
        real_via = [v for v in item.via if v in subject_set]
        if len(real_via) < 2:
            continue                     # 근거 부족 → 버린다
        # ② skill 이 통제 어휘인가
        canon = canonicalize(item.skill, strict=True)
        if not canon:
            continue
        out.append({"skill": canon, "via": real_via})

    # 같은 skill 이 두 번 나오면 via 를 합친다
    merged: dict[str, list[str]] = {}
    for item in out:
        merged.setdefault(item["skill"], [])
        merged[item["skill"]] += [v for v in item["via"] if v not in merged[item["skill"]]]
    return [{"skill": k, "via": v} for k, v in merged.items()]


# ═════════════════════════════════════════════════════════════

def load_grouped() -> pd.DataFrame:
    df = pd.read_csv(CSV)

    # 컬럼명이 다를 수 있으니 먼저 확인하고 멈춘다 (조용히 틀리는 것보다 낫다)
    need = {"학교명", "전공명", "과목명"}
    missing = need - set(df.columns)
    if missing:
        raise KeyError(f"컬럼 없음: {missing}. 실제 컬럼: {list(df.columns)}")

    if TARGET_SCHOOLS:
        df = df[df["학교명"].isin(TARGET_SCHOOLS)]

    df = df.dropna(subset=["전공명", "과목명"]).drop_duplicates(["학교명", "전공명", "과목명"])
    # groupby: SQL 의 GROUP BY 와 같다. 학교+전공으로 묶고 과목명을 리스트로 모은다
    return df.groupby(["학교명", "전공명"])["과목명"].apply(list).reset_index()


def build(sample: int = 0) -> None:
    grouped = load_grouped()
    SAMPLE_MAJORS = ["컴퓨터공학부", "산업공학과", "통계학과", "수리과학부", "경영학과"]

    if sample:
        grouped = grouped[grouped["전공명"].isin(SAMPLE_MAJORS)]   # head(sample) 대신

    print(f"대상 전공 {len(grouped)}개 (대학 {grouped['학교명'].nunique()}곳)")

    cache: dict = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    chain = build_chain()

    for i, row in grouped.iterrows():
        key = f"{row['학교명']}--{row['전공명']}"
        if key in cache:
            continue
        cache[key] = extract_skills(row["전공명"], row["과목명"], chain)
        print(f"  [{len(cache)}/{len(grouped)}] {key} → {[s['skill'] for s in cache[key]]}")
        CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── graph.json 의 majors 만 교체. jobs 는 건드리지 않는다
    majors = []
    for key, items in cache.items():
        if not items:
            continue                      # 역량 0개면 그래프에 올려도 안 이어진다
        school, name = key.split("--", 1)
        majors.append({
            "id": key, "school": school, "name": name,
            "develops": {it["skill"]: it["via"] for it in items},
        })

    graph = json.loads(GRAPH.read_text(encoding="utf-8")) if GRAPH.exists() else {"jobs": []}
    graph["majors"] = majors
    major_skills = {s for m in majors for s in m["develops"]}
    job_skills = {s for j in graph.get("jobs", []) for s in j["requires"] + j["prefers"]}
    graph["skills"] = sorted(major_skills | job_skills)
    GRAPH.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

    both = major_skills & job_skills
    print(f"\nMajor {len(majors)}개 / Job {len(graph.get('jobs', []))}개 / Skill {len(graph['skills'])}개")
    print(f"★ 양쪽 공통 Skill {len(both)}개: {sorted(both)}")
    print("  이 숫자가 5개 미만이면 추천이 거의 안 된다. 어휘집을 먼저 손봐야 한다.")


if __name__ == "__main__":
    build(sample=5 if len(sys.argv) > 1 and sys.argv[1] == "sample" else 0)
