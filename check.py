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