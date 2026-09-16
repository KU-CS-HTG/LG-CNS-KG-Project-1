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


@lru_cache(maxsize=1)
def _idf() -> dict[str, float]:
    """역량별 IDF (inverse document frequency) — 전공 쪽 기준.

    전공 63개 중 42개가 Data Analysis 를 기르고 3개만 Signal Processing 을 기른다. 둘을 똑같이 1점으로 세면
    "데이터 분석" 태그는 42개 전공을 동점으로 만들고, 정작 변별력 있는 희귀 역량은 묻힌다 (9/15 실측).
    검색엔진의 TF-IDF 와 같은 발상: 흔한 단어(the, 데이터)는 덜 세고 드문 단어는 더 센다.

        idf(s) = log( 전공 수 / s 를 기르는 전공 수 )     ← 흔할수록 0 에 가깝고, 드물수록 커진다

    예 (전공 63개): Data Analysis 0.41 · Statistics 0.92 · Machine Learning 1.84 · Signal Processing 3.04
    """
    majors = _load().get("majors", [])
    n = max(len(majors), 1)
    df: dict[str, int] = {}
    for m in majors:
        for s in m.get("develops", {}):
            df[s] = df.get(s, 0) + 1
    return {s: math.log(n / c) for s, c in df.items()}


def _weight(skill: str) -> float:
    """태그 하나의 가중치 = √idf. 전공 쪽에 없는 태그(IS_A 자식, 예: Java)는 부모(Programming)의 IDF 를 쓴다.

    √ 를 씌우는 이유 (2026-09-15 평가셋 회귀): idf 를 그대로 쓰면 전공 3곳에만 있는 Programming(3.0)이
    Data Analysis + Statistics 를 합친 것보다 무거워져, "파이썬으로 데이터 정리" 한 마디가 관심 분야 둘을 눌렀다.
    검색엔진도 희귀도를 준선형(sublinear)으로 눌러 쓴다. 순서는 유지하고 격차만 줄인다.
    """
    idf = _idf()
    if skill in idf:
        return math.sqrt(idf[skill])
    parent = _is_a().get(skill)
    return math.sqrt(idf[parent]) if parent in idf else 1.0


EVIDENCE_FULL = 3   # 근거 과목이 이만큼이면 그 역량을 '확실히 기른다' 고 본다


def _strength(n_via: int) -> float:
    """전공이 역량을 얼마나 확실히 기르는가 — 근거 과목 수로. 1과목 0.33, 2과목 0.67, 3과목 이상 1.0.

    "근거 2개 미만이면 버린다" 규칙을 1개로 완화한 대신(대학 과목은 주제당 1개가 보통), 그 차이를 가중치로 남긴다.
    실측(2026-09-15): 이게 없으면 '컴퓨터프로그래밍개론' 한 과목으로 Programming 을 얻은 농업생명과학대학이
    Statistics 근거 14과목인 통계학과를 "데이터 분석·통계·파이썬" 입력에서 이겼다.
    """
    return min(1.0, n_via / EVIDENCE_FULL)


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

def find_majors_by_skills(skills: list[str], limit: int = 10,
                          tag_weights: dict[str, float] | None = None) -> list[dict]:
    """역량 태그 → 추천 전공.

    같은 전공명이 여러 대학에 있으면 **최상위 1개만** 남긴다 (설계서 2절).
    안 그러면 추천 3개가 전부 컴퓨터공학과가 된다 — 확인 항목 2번.

    tag_weights: 태그별 신뢰 가중치 (기본 1.0). 성향에서 추정한 태그(vocab.TRAIT_TO_SKILL)는 0.5 로 들어온다 —
    근거(과목명·공고)가 아니라 연관에서 온 태그라 절반만 믿는다. 분자·분모에 같이 곱하므로 비율 의미는 유지된다.
    """
    user = set(skills)
    tw = tag_weights or {}
    w = lambda s: _weight(s) * tw.get(s, 1.0)                 # 태그 무게 = √idf × 신뢰 가중치
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
            "skills": sorted(develops),                    # 이 전공이 기르는 역량 전체 — 직무 검색은 이걸로 한다 (설계서 4절 ②)
            "family": family,                              # {사용자 태그: 그것을 커버한 전공 역량}
            # 각 역량이 어느 과목에서 나왔는지 — 출력 2칸의 "근거 과목". 계열 커버는 상위 개념의 과목이 근거
            "evidence": {s: develops[s] for s in matched + covered_by},
            # 전공 점수 = IDF 가중 커버리지. "사용자 태그의 무게 중 이 전공이 채운 무게의 비율". 계열 일치는 절반.
            #   - 왜 분모에 전공 쪽 크기를 넣지 않나: 직무처럼 집합 코사인을 쓰면 역량이 '적은' 전공이 이긴다.
            #     실측(9/15): "데이터 분석·통계" 에 식물생산과학부·의예과·화학부(역량 2개)가 1.0 공동 1위, 통계학과는 0.82.
            #   - 왜 IDF 가중: 42개 전공이 가진 Data Analysis 와 3개만 가진 Signal Processing 을 같은 1점으로 세면
            #     흔한 태그가 동점을 양산한다. 시험 계산(9/15): "신호처리·데이터분석" 에서 Data Analysis 만 있는
            #     첨단융합학부가 0.50 → 0.12 로 내려가고, 희귀 역량을 갖춘 전공이 위로 온다.
            #   태그가 전부 흔한 것뿐이면(분모가 작으면) 결과는 가중 전과 같다 — 해가 되는 경우가 없다.
            "score": (sum(w(s) * _strength(len(develops[s])) for s in exact)
                      + FAMILY_WEIGHT * sum(w(s) * _strength(len(develops[p])) for s, p in family.items()))
                     / sum(w(s) for s in user) if user else 0.0,
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

def find_jobs_by_skills(skills: list[str], limit: int = 5, career_type: str | None = None,
                        soft_traits: list[str] | None = None) -> list[dict]:
    """역량 태그 → 추천 직무. 갖춘 역량 / 채울 역량을 함께 돌려준다.

    career_type="신입" 이면 신입 공고만. 서비스 정의가 'LG 계열사 **신입** 직무 진로 추천' 이라
    취준생에게 경력·석박사 산학장학 공고가 1위로 나오는 걸 막는다 (실측 9/15: 웹/자바 입력에 '보험 SE (경력)' 이 1위).

    soft_traits: 학생의 강점 성향(한글, user_analysis STANDARD_TRAITS). vocab.TRAIT_TO_SOFT 로 소프트 스킬로 바꿔
    직무의 요구 태도(job["soft"])와 대조한다. **점수에는 더하지 않고 동점일 때만** 2차 기준 —
    soft 데이터가 없는 직무(84건 중 40건)가 '알 수 없음' 때문에 밀리면 안 되기 때문. 맞는 개수만 세고 안 맞는 건 세지 않는다.
    """
    from vocab import TRAIT_TO_SOFT
    user = set(skills)
    user_soft = {TRAIT_TO_SOFT[t] for t in (soft_traits or []) if t in TRAIT_TO_SOFT}
    ranked = []

    for j in _load().get("jobs", []):
        if career_type and career_type not in (j.get("career_type") or ""):
            continue
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
            "soft_wanted": list(j.get("soft", [])),               # 직무가 요구하는 태도 (없으면 빈 리스트 = 알 수 없음)
            "soft_match": sorted(set(j.get("soft", [])) & user_soft),   # 그중 학생 성향과 맞는 것
        })

    # 1차: 기술 매칭 점수. 2차(동점일 때만): 성향 적합 개수 — 데이터 없음(0)과 불일치(0)는 같은 급, 일치만 앞으로.
    # "동점" = 인접한 직무와의 점수 차 ≤ TIE_EPS. (반올림으로 묶으면 0.4763/0.4714 처럼 경계에 걸린 쌍이 갈린다 — 실측)
    ranked.sort(key=lambda x: -x["score"])
    return _reorder_ties(ranked, key=lambda x: len(x["soft_match"]))[:limit]


TIE_EPS = 0.01   # 이 차이 안이면 기술 점수는 같은 급으로 본다


def _reorder_ties(ranked: list[dict], key) -> list[dict]:
    """점수순 리스트를 받아, 점수가 TIE_EPS 안에서 이어지는 구간(동점 그룹)마다 key 내림차순으로 재정렬한다.
    그룹 밖의 순서(기술 점수)는 절대 바뀌지 않는다 — 성향은 기술 매칭을 뒤집지 못한다."""
    out: list[dict] = []
    i = 0
    while i < len(ranked):
        j = i + 1
        while j < len(ranked) and ranked[j - 1]["score"] - ranked[j]["score"] <= TIE_EPS:
            j += 1
        group = ranked[i:j]
        group.sort(key=lambda x: (-key(x), -x["score"]))
        out.extend(group)
        i = j
    return out


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
    """그래프에 있는 Skill 노드 전체 (전공·직무·상위 개념)."""
    return _load().get("skills", [])


def taggable_skills() -> list[str]:
    """사용자 태그 후보 — 전공이 기르는 역량 + 그 하위 개념(IS_A 자식).

    직무 쪽에만 있는 역량(예: 직무 required 에 적힌 Problem Solving, Excel)이 태그가 되면 어느 전공과도 안 맞으면서
    커버리지 분모만 키운다 (9/15 실측). 태그는 전공 매칭의 입력이므로 "전공이 기를 수 있는 것" 으로 제한한다.
    하위 개념을 포함하는 이유: 'Java' 태그는 전공의 'Programming' 으로 계열 커버되므로 유효한 태그다.
    """
    developed = {s for m in _load().get("majors", []) for s in m.get("develops", {})}
    children = {c for c, p in _is_a().items() if p in developed}
    return sorted(developed | children)


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
