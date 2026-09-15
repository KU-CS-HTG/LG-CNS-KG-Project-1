"""
build_graph_majors.py — subject_cleaned.csv → graph.json 의 전공 절반 (담당: C)

설계서 2절 그대로:
  과목명만 있고 과목 설명이 없다 → 과목 단위로 뽑으면 LLM의 상식일 뿐이다.
  전공 단위로 40~60개 과목을 한 번에 보여주면 성격이 선명해진다.

호출 수: 전공 1개당 LLM 1회. 서울대 단일이면 약 105회.

실행:
    python build_graph_majors.py sample     # 5개만 시범 추출 (반드시 먼저, 눈으로 확인)
    python build_graph_majors.py            # 전체 배치

파일 (3층 보관 — 직무 쪽 transform_v2 와 같은 원칙):
    data/majors_raw.json        LLM 원출력 캐시. 필터 전. ★ 커밋 대상 — 있으면 LLM을 다시 부르지 않는다
    data/majors_extracted.json  필터 통과분. raw 에서 매번 다시 계산 (0원, 몇 초)
    data/graph.json             majors 만 교체. jobs 는 build_graph_jobs.py 몫

필터(검증 규칙)를 고쳤을 때는 그냥 다시 실행하면 된다 — raw 캐시가 있으므로 LLM 호출 없이 필터만 다시 돈다.
LLM 을 다시 부르고 싶을 때만 data/majors_raw.json 을 지운다.
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
RAW_CACHE = DATA / "majors_raw.json"       # LLM 원출력 (필터 전). 직무 쪽 extracted_raw.json 과 같은 역할
EXTRACTED = DATA / "majors_extracted.json" # 필터 통과분. raw 에서 재계산되므로 캐시가 아니다
GRAPH = DATA / "graph.json"

# 대상 대학 — 월요일에 3개로 확정 (설계서 0절)
TARGET_SCHOOLS: list[str] = []           # 빈 리스트면 전체. 확정되면 여기에 3개 적는다

MAX_SUBJECTS = 80                        # 한 전공에서 LLM에 보여줄 과목 수 상한 (토큰 방어)

# 전공 쪽에서는 쓰지 않는 역량. CANON 에는 남겨 둔다 (직무 쪽은 계속 쓴다).
#   Communication / Problem Solving — 과목명으로 근거를 댈 수 없는 소프트 스킬. 9/15 전체 배치에서
#     각각 50·59개 전공(성악과·관현악과 포함)에 붙었고, 이 둘만 있는 전공이 10개였다.
#     기술 오분류를 막았더니 LLM 이 "뭐라도 고르기"의 출구를 여기로 옮긴 것. 사용자 태그에 들어오면 59개 전공 동점.
#   Knowledge Graph — 서울대에 지식그래프 과목이 없다. 인문계 7곳에 붙은 것은 전부 환각.
MAJOR_SKIP: set[str] = {"Communication", "Problem Solving", "Knowledge Graph"}


# ═════════════════════════════════════════════════════════════
# LLM 출력 스키마
# ═════════════════════════════════════════════════════════════

class SkillEvidence(BaseModel):
    """역량 하나 + 그 근거가 된 과목들."""
    skill: str = Field(description="역량명. 통제 어휘 목록 안에서만 고른다")
    via: list[str] = Field(description="근거 과목명. 반드시 입력으로 준 과목 목록에 있는 것만")


class MajorSkills(BaseModel):
    # "4~8개" 처럼 개수를 고정하면 모델이 개수를 맞추려고 내용을 지어낸다 (9/11 my_service "정확히 3개" 와 같은 함정).
    # 그래서 하한을 두지 않는다. 해당 없는 전공은 빈 리스트가 정답이다.
    skills: list[SkillEvidence] = Field(
        description="이 전공이 기르는 역량. 해당하는 것이 없으면 빈 리스트. 최대 8개",
        max_length=8,
    )


EXTRACT_SYSTEM = """너는 대학 교육과정을 분석해 전공이 기르는 역량을 판별하는 전문가다.

입력: 전공명 + 그 전공의 개설 과목명 목록
출력: 이 전공이 기르는 역량. 각 역량마다 근거가 된 과목명을 함께.

[엄격한 규칙]
1. `skill` 은 아래 통제 어휘 목록에 있는 것만 쓴다. 목록에 없는 역량은 만들지 않는다.
2. `via` 는 입력으로 준 과목 목록에 있는 과목명을 그대로 쓴다. 줄이거나 바꾸지 않는다.
3. 과목명이 그 역량을 **직접** 가리켜야 한다. 분위기가 비슷한 정도로는 안 된다.
4. 해당하는 역량이 없으면 skills 를 **빈 배열로 두는 것이 정답이다.**
   억지로 채우지 마라. 0개가 정상인 전공이 많다.

[이런 건 틀린 답이다 — 실제로 나왔던 오류]
  ✗ 간호학과 '의료관련감염관리' → Security
     Security 는 정보보안이다. 감염 관리와 무관하다.
  ✗ 역사학부 '한국사를 보는 관점' → Knowledge Graph
     Knowledge Graph 는 데이터를 노드와 엣지로 다루는 기술이다.
  ✗ 에너지자원공학과 '이산화탄소 포집' → Cloud
     Cloud 는 클라우드 컴퓨팅이다. 에너지와 무관하다.
  ✗ 국어교육과 '한국문학교육론' → Knowledge Graph

[이런 건 맞는 답이다]
  ✓ 컴퓨터공학부 '데이터베이스' → Database
  ✓ 통계학과 '회귀분석 및 실습', '수리통계' → Statistics
  ✓ 전기·정보공학부 '딥러닝의 기초' → Deep Learning

[통제 어휘 목록]
{vocab_list}"""


def build_chain():
    from dotenv import load_dotenv
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    from vocab import CANON

    load_dotenv()
    vocab_list = ", ".join(sorted(set(CANON.values()) - MAJOR_SKIP))   # 전공 쪽 제외 역량은 목록에서도 뺀다

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", EXTRACT_SYSTEM),
        ("human", "전공명: {major}\n\n개설 과목 ({n}개):\n{subjects}"),
    ]).partial(vocab_list=vocab_list)
    return prompt | llm.with_structured_output(MajorSkills)


def call_llm(major: str, subjects: list[str], chain=None) -> list[dict]:
    """LLM 호출만 한다. 필터 없이 원출력을 그대로 돌려준다 (raw 층).

    돈이 드는 유일한 함수. 결과는 build() 가 data/majors_raw.json 에 캐시한다.
    """
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
    # pydantic 객체 → dict. model_dump() 는 필드를 그대로 딕셔너리로 푼다
    return [item.model_dump() for item in result.skills]


def match_subject(name: str, subjects: list[str]) -> str | None:
    """LLM 이 적은 과목명을 실제 과목명에 맞춘다. 정확 일치가 없으면 부분 일치를 1건까지 허용.

    '기계학습' → '기계학습 개론' 처럼 LLM 이 줄여 쓰는 일이 잦다. 예전 코드는 정확 일치만 인정해서
    이런 근거가 전부 탈락했다. 단, 후보가 2개 이상이면 어느 과목인지 알 수 없으므로 None (안전 쪽).
    """
    name = name.strip()
    if name in subjects:
        return name
    if len(name) < 2:                          # 'AI' 한 글자짜리 등은 부분 일치 시도 안 함
        return None
    cands = [s for s in subjects if name in s or s in name]
    return cands[0] if len(cands) == 1 else None


def filter_skills(raw: list[dict], subjects: list[str]) -> list[dict]:
    """검증 2겹 (환각 검사). LLM 을 부르지 않는 순수 함수라 몇 번이고 다시 돌릴 수 있다.

    순서: ① via 검증 → ② skill 정규화.  (정규화를 먼저 하면 정상 변환까지 환각으로 잡힌다)
    """
    shown = subjects[:MAX_SUBJECTS]
    out: list[dict] = []
    for item in raw:
        # ① via 가 실제 과목인가 — 부분 일치 허용, 중복 제거
        real_via = [m for m in (match_subject(v, shown) for v in item.get("via", [])) if m]
        real_via = list(dict.fromkeys(real_via))
        if not real_via:
            continue                     # 근거 0개 → 버린다.  (예전: 2개 미만이면 버림 → 대학 과목은 주제당 1개라 거의 다 탈락했다)
        # ② skill 이 통제 어휘인가
        canon = canonicalize(item.get("skill", ""), strict=True)
        if not canon or canon in MAJOR_SKIP:   # 통제 어휘 밖이거나 전공 쪽 제외 역량이면 버린다
            continue
        out.append({"skill": canon, "via": real_via})

    # 같은 skill 이 두 번 나오면 via 를 합친다
    merged: dict[str, list[str]] = {}
    for item in out:
        merged.setdefault(item["skill"], [])
        merged[item["skill"]] += [v for v in item["via"] if v not in merged[item["skill"]]]
    return [{"skill": k, "via": v} for k, v in merged.items()]


def extract_skills(major: str, subjects: list[str], chain=None) -> list[dict]:
    """설계서 4절 계약 함수. 전공 1개 → [{"skill":..., "via":[...]}]  (= call_llm → filter_skills)"""
    return filter_skills(call_llm(major, subjects, chain), subjects)


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

    # ── 1단계: LLM 호출 (raw 캐시에 없는 전공만). 돈이 드는 유일한 구간
    raw_cache: dict = json.loads(RAW_CACHE.read_text(encoding="utf-8")) if RAW_CACHE.exists() else {}
    chain = None                          # 실제로 호출할 전공이 있을 때만 만든다
    for _, row in grouped.iterrows():
        key = f"{row['학교명']}--{row['전공명']}"
        if key in raw_cache:
            continue
        chain = chain or build_chain()
        raw_cache[key] = call_llm(row["전공명"], row["과목명"], chain)
        print(f"  [LLM {len(raw_cache)}/{len(grouped)}] {key} → 원출력 {len(raw_cache[key])}개")
        RAW_CACHE.write_text(json.dumps(raw_cache, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 2단계: 필터 (raw → extracted). LLM 없음, 0원. 규칙을 고치면 여기만 다시 돈다
    extracted: dict = {}
    for _, row in grouped.iterrows():
        key = f"{row['학교명']}--{row['전공명']}"
        raw = raw_cache.get(key, [])
        kept = filter_skills(raw, row["과목명"])
        extracted[key] = kept
        # 필터가 무엇을 버렸는지 보여준다 — "조용히 틀리는" 걸 막는 가장 싼 장치
        kept_names = {k["skill"] for k in kept}
        dropped = sorted({r.get("skill", "") for r in raw
                          if (canonicalize(r.get("skill", ""), strict=True) or r.get("skill")) not in kept_names})
        print(f"  {key} → raw {len(raw)} / 채택 {len(kept)} {sorted(kept_names)}"
              + (f"  (탈락: {dropped})" if dropped else ""))

    if sample:
        print("\n(sample 모드: 눈으로 확인만. majors_extracted.json / graph.json 은 쓰지 않는다)")
        return
    EXTRACTED.write_text(json.dumps(extracted, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── graph.json 의 majors 만 교체. jobs 는 건드리지 않는다
    majors = []
    for key, items in extracted.items():
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
