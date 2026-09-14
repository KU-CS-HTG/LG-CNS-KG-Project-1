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

import json
import math
from functools import lru_cache
from pathlib import Path

GRAPH = Path("graph.json")


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
        matched = sorted(user & set(develops))
        if not matched:
            continue
        ranked.append({
            "id": m["id"],
            "school": m["school"],
            "name": m["name"],
            "matched_skills": matched,
            # 각 역량이 어느 과목에서 나왔는지 — 출력 2칸의 "근거 과목"
            "evidence": {s: develops[s] for s in matched},
            "score": _score(user, set(develops)),
        })

    ranked.sort(key=lambda x: -x["score"])

    # 전공명 기준 중복 제거. 이미 점수순이므로 먼저 나온 것이 최상위다.
    seen: set[str] = set()
    unique = []
    for m in ranked:
        if m["name"] in seen:
            continue
        seen.add(m["name"])
        unique.append(m)

    return unique[:limit]


def find_jobs_by_skills(skills: list[str], limit: int = 5) -> list[dict]:
    """역량 태그 → 추천 직무. 갖춘 역량 / 채울 역량을 함께 돌려준다."""
    user = set(skills)
    ranked = []

    for j in _load().get("jobs", []):
        req, pref = set(j["requires"]), set(j["prefers"])
        all_skills = req | pref
        have = sorted(user & all_skills)
        if not have:
            continue
        ranked.append({
            "id": j["id"],
            "role": j["role"],
            "company": j["company"],
            "career_type": j["career_type"],
            "url": j["url"],
            "have": have,                          # 갖춘 역량
            "gap": sorted(req - user),             # 채울 역량 — 필수 중 없는 것만
            "score": _score(user, all_skills),
        })

    ranked.sort(key=lambda x: -x["score"])
    return ranked[:limit]


def get_evidence(major_id: str, skill: str) -> list[str]:
    """전공 × 역량 → 근거 과목명. 없으면 빈 리스트."""
    for m in _load().get("majors", []):
        if m["id"] == major_id:
            return m.get("develops", {}).get(skill, [])
    return []


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
