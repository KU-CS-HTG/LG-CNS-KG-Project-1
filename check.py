"""check.py — 확인 3건 (담당: D)"""
import graph_store as gs
from app import run, render

a = run(["데이터 분석이 재미있어요", "숫자에 강해요", "①"], {})
b = run(["숫자 다루는 게 좋아요", "분석을 잘해요", "① 데이터를 파고드는 쪽"], {})
assert not a.get("empty") and not b.get("empty"), "역량이 검출되지 않음 → 태그 정규화 또는 graph.json 확인"
assert a["major"]["name"] == b["major"]["name"], \
    f"재현성 실패: {a['major']['name']} vs {b['major']['name']} → 어휘집 확인"

j = a["job"]
assert j["covered_count"] + len(j["gap"]) <= j["total"], "집합 연산 오류"

text = render(a)
all_subj = {v for m in gs._load()["majors"] for vs in m["develops"].values() for v in vs}
given = {s["subject"] for s in a["subjects"]}
# 부분 문자열 오탐 방지: '자료분석 및 실습' 은 '다변량자료분석 및 실습' 안에도 들어 있다.
# 준 과목명 안에 통째로 포함되는 이름은 누출이 아니다.
leaked = [s for s in (all_subj - given) if s in text and not any(s in g for g in given)]
assert not leaked, f"주지 않은 과목이 등장: {leaked}"

print("확인 3건 통과")
# ═════════════════════════════════════════════════════════════
# 평가셋 (evals/cases.json) — 매칭을 고칠 때마다 이걸로 판단한다. 눈으로 서너 개 보고 결정하지 않는다.
#   기준은 느슨하게: 기대 전공이 상위 3위 안 / 기대 직무명 조각이 상위 2개 직무 중 하나에 포함.
#   (태그는 LLM 이 뽑으므로 표현이 조금만 달라도 1위가 흔들릴 수 있다 — 그래서 top-3)
# ═════════════════════════════════════════════════════════════
import json
from pathlib import Path

cases = json.loads((Path(__file__).resolve().parent / "evals" / "cases.json").read_text(encoding="utf-8"))
passed = 0
print(f"\n평가셋 {len(cases)}건")
for c in cases:
    s: dict = {}
    r = run(c["answers"], s)
    if "followup" in r:                                   # 재질문이 나오면 첫 답을 한 번 더 준다
        r = run(c["answers"] + [c["answers"][0]], s)
    if r.get("empty"):
        print(f"  ✗ #{c['id']:2} 역량 미검출  tags={r.get('tags')}")
        continue
    top3 = [x["name"].replace("?", "·") for x in r["ranking"][:3]]
    jobs = [j["role"] for j in r.get("jobs", [])]
    ok_major = any(m in top3 for m in c["expect_major_top3"])
    ok_job = (not c["expect_job_role_contains"]) or any(k in j for k in c["expect_job_role_contains"] for j in jobs)
    ok = ok_major and ok_job
    passed += ok
    print(f"  {'✓' if ok else '✗'} #{c['id']:2} 전공 {top3[0]:<14} 직무 {jobs[0] if jobs else '-':<22} "
          f"{'' if ok_major else '← 전공 기대: ' + '/'.join(c['expect_major_top3'])} "
          f"{'' if ok_job else '← 직무 기대: ' + '/'.join(c['expect_job_role_contains'])}  {c['note'][:30]}")
print(f"통과 {passed}/{len(cases)}")

# ═════════════════════════════════════════════════════════════
# 인터뷰 모드 (evals/interview_cases.json) — user_analysis 어댑터를 대본으로 자동 실행
#   ask() 에 대본을 주입하므로 키보드 입력 없이 돈다. 건당 LLM 최대 3회 + 태거 1회.
# ═════════════════════════════════════════════════════════════
from interview import interview

icases = json.loads((Path(__file__).resolve().parent / "evals" / "interview_cases.json").read_text(encoding="utf-8"))
ipassed = 0
print(f"\n인터뷰 모드 {len(icases)}건")
for c in icases:
    lines = iter(c["script"])
    iv = interview(ask=lambda _prompt="": next(lines), say=lambda _m: None)
    r = run(iv["answers"] + [c["q3"]], {}, trait_tags=iv["trait_tags"])
    if "followup" in r or r.get("empty"):
        print(f"  ✗ {c['id']} 결과 없음 ({'재질문' if 'followup' in r else '미검출'})"); continue
    top3 = [x["name"].replace("?", "·") for x in r["ranking"][:3]]
    ok_major = any(m in top3 for m in c["expect_major_top3"])
    ok_trait = set(c["expect_trait_tags_subset"]) <= set(iv["trait_tags"]) | set(r["tags"])
    ok = ok_major and ok_trait
    ipassed += ok
    print(f"  {'✓' if ok else '✗'} {c['id']} 전공 {top3[0]:<12} LLM {iv['llm_calls']}회 성향태그 {iv['trait_tags']} "
          f"{'' if ok_major else '← 전공 기대: ' + '/'.join(c['expect_major_top3'])} {'' if ok_trait else '← 성향 기대 미충족'}  {c['note'][:28]}")
print(f"통과 {ipassed}/{len(icases)}")
