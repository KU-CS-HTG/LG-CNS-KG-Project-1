from graph_store import find_majors_by_skills, find_jobs_by_skills, all_skills

QUESTIONS = [
    "관심 있는 분야나 하고 싶은 일을 자유롭게 적어주세요.",
    "스스로 잘한다고 생각하는 것은 무엇인가요?",
    "혼자 파고드는 편인가요, 같이 굴러가는 편인가요?",
]

def run(answers: list[str], session: dict) -> dict:
    tags = normalize_to_tags(answers)                    # LLM 1회. 통제 어휘로만

    if len(tags) < 2 and not session.get("asked_again"):  # 조건부 분기, 최대 1회
        session["asked_again"] = True
        return {"followup": QUESTIONS[0]}

    session["tags"] = list(dict.fromkeys(session.get("tags", []) + tags))

    majors = find_majors_by_skills(session["tags"], limit=3)
    jobs = find_jobs_by_skills(session["tags"], limit=2)
    return {"tags": session["tags"], "majors": majors, "jobs": jobs}