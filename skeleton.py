# skeleton.py — 전부 가짜지만, 끝까지 돈다
def normalize(answers):        return ["데이터분석", "논리적사고"]
def score_all_majors(skills):  return [{"major": "산업공학과", "score": 8.2},
                                       {"major": "컴퓨터공학부", "score": 7.9}]
def find_job(skills):          return {"job": "데이터 엔지니어", "requires": ["데이터분석","SQL","클라우드"]}
def subjects_for(major, job):  return ["데이터마이닝", "최적화이론"]

def run(answers):
    skills  = normalize(answers)
    ranking = score_all_majors(skills)
    job     = find_job(skills)
    gap     = set(job["requires"]) - set(skills)      # ← 설계서 2절의 그 한 줄
    print(f"[전공] {ranking[0]['major']} — {len(ranking)}개 중 1위")
    print(f"[직무] {job['job']} — {len(job['requires'])}개 중 {len(job['requires'])-len(gap)}개 커버")
    print(f"[갭]   {', '.join(gap)}")

run(["데이터 다루는 일 하고 싶음", "논리적으로 따지는 거", "혼자 파는 편"])