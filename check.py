"""check.py — 확인 3건 (담당: D)"""
import graph_store as gs
from app import run, render

a = run(["데이터 분석이 재미있어요", "숫자에 강해요", "①"], {})
b = run(["숫자 다루는 게 좋아요", "분석을 잘해요", "① 데이터를 파고드는 쪽"], {})
assert a["major"]["name"] == b["major"]["name"], \
    f"재현성 실패: {a['major']['name']} vs {b['major']['name']} → 어휘집 확인"

j = a["job"]
assert j["covered_count"] + len(j["gap"]) <= j["total"], "집합 연산 오류"

text = render(a)
all_subj = {v for m in gs._load()["majors"] for vs in m["develops"].values() for v in vs}
given = {s["subject"] for s in a["subjects"]}
leaked = [s for s in (all_subj - given) if s in text]
assert not leaked, f"주지 않은 과목이 등장: {leaked}"

print("확인 3건 통과")