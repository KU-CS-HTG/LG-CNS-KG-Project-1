"""
graph_store.py — graph.json 조회 전용 (담당: B)

설계서 4절 계약:
    find_majors_by_skills(skills, limit=10) -> list[dict]
    find_jobs_by_skills(skills, limit=5)    -> list[dict]
    get_evidence(major_id, skill)           -> list[str]

★ 이 모듈에는 LLM이 없다. 순수 딕셔너리 조회다.
  "판정을 LLM에서 도구로 넘긴다"(설계서 8절 4장)가 여기서 실현된다.
  LLM은 사용자 문장을 태그로 바꾸는 일만 하고, 무엇을 추천할지는 이 함수들이 정한다.
  그래서 같은 입력이면 항상 같은 결과가 나온다 — 확인 항목 1번이 통과하는 이유.
"""

from __future__ import annotations

from collections import Counter
import json
import math
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"   # 이 파일이 있는 폴더 기준 → 어디서 실행해도 같은 경로
GRAPH = DATA / "graph.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    """graph.json 을 한 번만 읽어 메모리에 둔다.

    lru_cache: 같은 인자로 다시 부르면 계산 없이 이전 결과를 돌려주는 데코레이터.
    요청마다 파일을 다시 읽으면 느리다. 파일을 바꿨으면 _load.cache_clear() 를 부른다.
    """
    return json.loads(GRAPH.read_text(encoding="utf-8"))


def _score(user: set[str], target: set[str]) -> float:
    """겹치는 정도. 집합 코사인.

    그냥 len(user & target) 으로 세면 **역량을 많이 나열한 쪽이 항상 이긴다.**
    실측: 직무당 역량 개수가 0~8개로 편차가 크다.
    분모 √(|A|×|B|) 가 그 길이 차이를 보정한다.
    """
    if not user or not target:
        return 0.0
    return len(user & target) / math.sqrt(len(user) * len(target))


FAMILY_WEIGHT = 0.5   # 계열 일치(상위 개념으로 커버)는 정확 일치의 절반으로 센다


def _is_a() -> dict[str, str]:
    """IS_A 엣지 (자식 → 부모). graph.json 의 "is_a". 없으면 빈 dict — 계층 없이도 동작한다."""
    return _load().get("is_a", {})


def _match(need: set[str], have: set[str]) -> tuple[set[str], dict[str, str]]:
    """'need' 쪽 역량 하나하나를 'have' 쪽이 커버하는지 — 정확 일치와 계열 일치로 나눠 돌려준다.

    exact  : need 의 역량이 have 에 그대로 있다                          (Data Analysis)
    family : need 의 역량은 없지만 그 **상위 개념**이 have 에 있다        (Oracle ← Database)
             {need 의 역량: 그것을 커버한 have 의 상위 개념}

    ★ 방향: need 를 위로 올려서 비교한다. have 를 아래로 내리지 않는다.
      "직무가 Oracle 을 요구 → Database 계열을 요구" 는 참이지만,
      "전공이 Database 를 가르침 → Oracle 을 가르침" 은 근거 없는 구체화(환각)다.
      Neo4j 로 쓰면 (need)-[:IS_A*0..1]->(have) — 0홉이 exact, 1홉이 family.
    """
    is_a = _is_a()
    exact = need & have
    family = {s: is_a[s] for s in need - exact if is_a.get(s) in have}
    return exact, family


# ═════════════════════════════════════════════════════════════

def find_majors_by_skills(skills: list[str], limit: int = 10) -> list[dict]:
    """역량 태그 → 추천 전공.

    같은 전공명이 여러 대학에 있으면 **최상위 1개만** 남긴다 (설계서 2절).
    안 그러면 추천 3개가 전부 컴퓨터공학과가 된다 — 확인 항목 2번.
    """
    user = set(skills)
    ranked = []

    for m in _load().get("majors", []):
        develops = m.get("develops", {})
        # 사용자 태그(need)를 전공 역량(have)에 맞춘다. 태그 'Java' 는 전공의 'Programming' 으로 계열 커버.
        exact, family = _match(user, set(develops))
        if not exact and not family:
            continue
        matched = sorted(exact)
        covered_by = sorted(set(family.values()))          # 계열 커버에 쓰인 전공 쪽 상위 개념
        ranked.append({
            "id": m["id"],
            "school": m["school"],
            "name": m["name"],
            "matched_skills": matched,
            "family": family,                              # {사용자 태그: 그것을 커버한 전공 역량}
            # 각 역량이 어느 과목에서 나왔는지 — 출력 2칸의 "근거 과목". 계열 커버는 상위 개념의 과목이 근거
            "evidence": {s: develops[s] for s in matched + covered_by},
            # 전공 점수 = 사용자 태그 중 이 전공이 기르는 비율 (커버리지). 계열 일치는 절반.
            #   직무처럼 집합 코사인을 쓰면 역량이 '적은' 전공이 이긴다 — 실측(9/15): "데이터 분석·통계" 에
            #   식물생산과학부·의예과·화학부(역량 2개)가 1.0 으로 공동 1위, 통계학과(역량 3개)는 0.82 로 밀렸다.
            #   전공은 역량이 많다고 나쁠 이유가 없으므로 분모에 전공 쪽 크기를 넣지 않는다.
            "score": (len(exact) + FAMILY_WEIGHT * len(family)) / len(user) if user else 0.0,
            # 동점 처리 — 매칭된 역량의 근거 과목 수. 같은 커버리지면 그 역량을 더 깊게 다루는 전공이 위로.
            #   (작업 가이드 B-3 "2차 기준". 통계학과는 Statistics 근거 과목이 19개, 식물생산과학부는 2개)
            "evidence_count": sum(len(develops[s]) for s in matched + covered_by),
        })

    # 정렬 기준을 튜플로 주면 앞에서부터 차례로 비교한다: 커버리지 → 근거 과목 수
    ranked.sort(key=lambda x: (-x["score"], -x["evidence_count"]))

    # 전공명 기준 중복 제거. 이미 점수순이므로 먼저 나온 것이 최상위다.
    seen: set[str] = set()
    unique = []
    for m in ranked:
        if m["name"] in seen:
            continue
        seen.add(m["name"])
        unique.append(m)

    return unique[:limit]

def count_majors() -> int:
    """그래프에 올라간 전공 수 (전공명 기준, 중복 제외)."""
    return len({m["name"] for m in _load().get("majors", [])})

def find_jobs_by_skills(skills: list[str], limit: int = 5) -> list[dict]:
    """역량 태그 → 추천 직무. 갖춘 역량 / 채울 역량을 함께 돌려준다."""
    user = set(skills)
    ranked = []

    for j in _load().get("jobs", []):
        req, pref = set(j["requires"]), set(j["prefers"])
        all_skills = req | pref
        # 직무 요구(need)를 전공 역량(have)에 맞춘다. 요구 'Oracle' 은 전공의 'Database' 로 계열 커버.
        exact, family = _match(all_skills, user)
        if not exact and not family:
            continue
        have = sorted(exact)
        ranked.append({
            "id": j["id"],
            "role": j["role"],
            "company": j["company"],
            "career_type": j["career_type"],
            "url": j["url"],
            "have": have,                                        # 정확히 갖춘 역량
            "family": family,                                    # {직무 요구: 그것을 커버한 전공 역량}  예: {"Oracle": "Database"}
            "gap": sorted(req - exact - set(family)),            # 채울 역량 — 필수 중 정확·계열 어느 쪽으로도 안 되는 것
            "total": len(all_skills),
            "covered_count": len(exact) + len(family),
            # 집합 코사인에 계열 일치를 절반으로 얹는다. 분모 √(|user|×|직무 역량|) 는 역량을 길게 나열한 공고 보정 (기존 그대로)
            "score": (len(exact) + FAMILY_WEIGHT * len(family)) / math.sqrt(len(user) * len(all_skills)),
        })

    ranked.sort(key=lambda x: -x["score"])
    return ranked[:limit]


def get_evidence(major_id: str, skill: str) -> list[str]:
    """전공 × 역량 → 근거 과목명. 없으면 빈 리스트."""
    for m in _load().get("majors", []):
        if m["id"] == major_id:
            return m.get("develops", {}).get(skill, [])
    return []

def subjects_for(major_id: str, skills: list[str], k: int = 3) -> list[dict]:
    """주어진 역량들을 기르는 과목을, 많이 걸리는 순으로 k개.

    한 과목이 여러 역량에 동시에 걸리면 위로 올라온다 — 자동으로 '가성비 과목'이 된다.
    """
    want = set(skills)
    counter: Counter = Counter()
    detail: dict[str, list[str]] = {}

    for m in _load().get("majors", []):
        if m["id"] != major_id:
            continue
        for skill, subjects in m.get("develops", {}).items():
            if skill not in want:
                continue
            for sub in subjects:
                counter[sub] += 1
                detail.setdefault(sub, []).append(skill)

    return [{"subject": n, "hits": c, "for": detail[n]} for n, c in counter.most_common(k)]

def all_skills() -> list[str]:
    """통제 어휘 전체. app.py 가 LLM 출력을 대조할 때 쓴다."""
    return _load().get("skills", [])


def exists(name: str) -> bool:
    """이 고유명사가 그래프에 실재하는가 — 확인 항목 3번의 자동 검사."""
    g = _load()
    names = (set(g.get("skills", []))
             | {m["name"] for m in g.get("majors", [])}
             | {m["school"] for m in g.get("majors", [])}
             | {j["role"] for j in g.get("jobs", [])}
             | {j["company"] for j in g.get("jobs", [])})
    return name in names


if __name__ == "__main__":
    user = ["Python", "SQL", "Java", "Machine Learning"]
    print(f"입력 역량: {user}\n")

    print("── 추천 전공")
    for m in find_majors_by_skills(user, limit=3):
        print(f"  {m['school']} {m['name']}  (score {m['score']:.3f})")
        for s, subjects in m["evidence"].items():
            print(f"      {s} ← {', '.join(subjects)}")

    print("\n── 추천 직무")
    for j in find_jobs_by_skills(user, limit=3):
        print(f"  [{j['company']}] {j['role']} ({j['career_type']})  score {j['score']:.3f}")
        print(f"      갖춘 역량: {j['have']}")
        print(f"      채울 역량: {j['gap']}")
