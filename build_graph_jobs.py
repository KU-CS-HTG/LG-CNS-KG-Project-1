"""
build_graph_jobs.py — 기존 직무 산출물 → graph.json 의 직무 절반 (담당: C)

설계서 v3 에 맞춰 기존 코드를 정리한 것:
  - NCS 제외 → ncs_code 필드 삭제
  - Neo4j 제외 → JSONL 대신 graph.json 하나로
  - 노드 3종/엣지 2종 → Job 노드에 requires / prefers 만 남김
  - 통제 어휘는 vocab.py 한 곳에서만 (transform_v2 의 ALIASES 는 그리로 이사)

입력 (있는 것을 자동으로 골라 씀)
  A) staged_jobs.json + extracted_raw.json   ← transform_v2 를 돌렸다면
  B) curated_jobs.jsonl                       ← v1 결과만 있다면

출력
  graph.json  (majors 는 비어 있음 — 전공 파이프라인이 채운다)
"""

from __future__ import annotations

import json
from pathlib import Path

from vocab import canonicalize_all, PARENT

DATA = Path(__file__).resolve().parent / "data"   # 이 파일이 있는 폴더 기준 → 어디서 실행해도 같은 경로
STAGED = DATA / "staged_jobs.json"
EXTRACTED = DATA / "extracted_raw.json"
CURATED_V1 = DATA / "curated_jobs.jsonl"
GRAPH = DATA / "graph.json"


def load_job_rows() -> list[dict]:
    """어떤 산출물이 있든 공통 형태로 읽어들인다."""
    if STAGED.exists() and EXTRACTED.exists():
        staged = {r["job_id"]: r for r in json.loads(STAGED.read_text(encoding="utf-8"))}
        extracted = json.loads(EXTRACTED.read_text(encoding="utf-8"))
        rows = []
        for jid, ext in extracted.items():
            s = staged.get(jid)
            if not s:
                continue
            rows.append({
                "job_id": jid,
                "role": s["role"],
                "company": s["company"],
                "career_type": s["career_type"],
                "source_url": s["source_url"],
                "required": ext.get("required_skills", []),
                "preferred": ext.get("preferred_skills", []),
            })
        print(f"입력: {STAGED.name} + {EXTRACTED.name} ({len(rows)}건)")
        return rows

    if CURATED_V1.exists():
        rows = []
        for line in CURATED_V1.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            rows.append({
                "job_id": r["job_id"],
                "role": r["role"],
                "company": r["company"],
                "career_type": r["career_type"],
                "source_url": r["source_url"],
                # v1은 required/preferred, v2는 required_skills/preferred_skills
                "required": r.get("required") or r.get("required_skills", []),
                "preferred": r.get("preferred") or r.get("preferred_skills", []),
            })
        print(f"입력: {CURATED_V1.name} ({len(rows)}건)")
        return rows

    raise FileNotFoundError("staged+extracted 또는 curated_jobs.jsonl 이 필요합니다")


def build_jobs() -> tuple[list[dict], set[str], list[str]]:
    """Job 노드 목록, 등장한 Skill 집합, CANON 추가 후보 목록."""
    jobs: list[dict] = []
    skills: set[str] = set()
    cand_all: list[str] = []

    for r in load_job_rows():
        req, c1, _ = canonicalize_all(r["required"])
        pref, c2, _ = canonicalize_all(r["preferred"])
        cand_all += c1 + c2

        # 필수에 이미 있는 건 우대에서 뺀다 (같은 역량이 양쪽에 뜨면 출력이 지저분해진다)
        pref = [s for s in pref if s not in set(req)]

        if len(req) + len(pref) < 2:
            continue                       # 역량 0~1개 직무는 제외. 1개짜리('영업마케팅: Data Analysis')는 집합 코사인에서
                                           # 항상 만점이 나와 AI 직무(10개)를 밀어내는데, 추천 근거로는 너무 빈약하다 (9/15 실측)

        jobs.append({
            "id": r["job_id"],
            "role": r["role"],
            "company": r["company"],
            "career_type": r["career_type"],
            "url": r["source_url"],
            "requires": req,
            "prefers": pref,
        })
        skills |= set(req) | set(pref)

    return jobs, skills, list(dict.fromkeys(cand_all))


def build() -> None:
    jobs, job_skills, candidates = build_jobs()

    # 기존 graph.json 이 있으면 majors 는 보존한다 (C와 전공 담당이 따로 돌려도 안 깨지게)
    existing = json.loads(GRAPH.read_text(encoding="utf-8")) if GRAPH.exists() else {}
    majors = existing.get("majors", [])

    major_skills = {s for m in majors for s in m.get("develops", {})}

    graph = {
        # 상위 개념(PARENT 의 값)도 Skill 노드다 — 전공이 아직 안 기르더라도 태그 후보에는 있어야 한다
        "skills": sorted(job_skills | major_skills | set(PARENT.values())),
        # IS_A 엣지: (:Skill 자식)-[:IS_A]->(:Skill 부모). 어휘집(vocab.PARENT)을 그래프 데이터로 옮긴 것.
        # graph_store 는 이걸로 "직무가 요구하는 Oracle ≈ 전공이 기르는 Database" 를 잇는다 (위로만).
        "is_a": dict(PARENT),
        "majors": majors,
        "jobs": jobs,
    }
    GRAPH.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

    # ── 리포트: 월요일에 눈으로 봐야 하는 숫자
    both = job_skills & major_skills
    print(f"\ngraph.json 저장")
    print(f"  Job   {len(jobs)}개")
    print(f"  Major {len(majors)}개")
    print(f"  Skill {len(graph['skills'])}개")
    print(f"  ★ 전공·직무 양쪽에 모두 등장한 Skill: {len(both)}개 {sorted(both)[:10]}")
    via_parent = {s for s in job_skills - major_skills if PARENT.get(s) in major_skills}
    print(f"  ★ 정확히는 안 겹치지만 IS_A 한 홉으로 전공과 이어지는 직무 역량: {len(via_parent)}개 {sorted(via_parent)[:12]}")
    print(f"    ↑ 이 숫자가 0이면 추천 결과도 0이다. 어휘집이 갈렸다는 뜻.")
    from collections import Counter
    by_company = Counter(j["company"] for j in jobs)
    print(f"  회사별 Job: {dict(by_company)}")

    # CANON 추가 후보 → 파일. A 가 이걸 보고 어휘집에 넣을지 결정한다 (작업 가이드 A-5 'unmapped.txt')
    cand_path = DATA / "canon_candidates.txt"
    counts = Counter(t.strip() for r in load_job_rows() for t in r["required"] + r["preferred"])
    ranked = sorted(candidates, key=lambda t: -counts.get(t, 0))          # 많이 나온 후보부터 — A 가 위에서부터 보면 된다
    cand_path.write_text("\n".join(f"{counts.get(t, 0)}\t{t}" for t in ranked), encoding="utf-8")
    print(f"\n  CANON 추가 후보 {len(candidates)}개 → {cand_path.name} (A에게 전달)")
    for t in candidates[:12]:
        print(f"    - {t}")


if __name__ == "__main__":
    build()
