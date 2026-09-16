"""interview.py — 대화형 입력 모드 (user_analysis 어댑터)

팀원이 만든 user_analysis/ (자기소개 → 7개 영역 프로필) 를 우리 파이프라인의 **입력 단계**로 붙인다.
user_analysis 의 파일은 건드리지 않는다. 이 파일이 둘 사이를 잇는 유일한 접점이다.

우리가 쓰는 것 (7개 영역 중 2개):
  interest  → domains·activities 를 먼저 **사전(vocab.canonicalize)** 으로 태그화 (LLM 0, 근거 = interest.evidence)
              사전에 없는 표현(미술, 음악…)만 자기소개 원문과 함께 태거(app.normalize_to_tags)로     ← 효과의 대부분
  strength  → mapped_traits(direction=strength) →
              ① vocab.TRAIT_TO_SKILL → 기술 역량 태그 (가중치 0.5, 전공 매칭용)
              ② vocab.TRAIT_TO_SOFT  → 소프트 스킬 → 직무의 요구 태도(job.soft)와 대조 (동점 처리 전용)
나머지 5개(약점·생활·친구·가치관·공부 스타일)는 매칭에 쓸 근거가 없어 호출하지 않는다 (코드는 그대로 보존).

세 가지 방법으로 프로필(StudentProfileAnalysis)을 채울 수 있고, 채운 다음엔 전부
profile_to_inputs() 하나로 수렴한다 — 대화든 파일이든 run() 이 받는 모양은 같다.

  interview()         — 데모용. 질문은 LLM 이 만들지 않고 PROFILE_AREAS 의 고정 질문(2개 영역, 영역당 최대 1회)을 쓴다.
                         (원본은 temperature=0.3 으로 질문을 생성해 매번 달라진다) 실행: python app.py --interview
  full_interview()    — user_analysis/main.py 와 동일한 흐름. question_agent 가 7개 영역 전부를 그때그때
                         물어본다(영역당 최대 2회). LLM 호출이 더 많은 대신 main.py 를 직접 돌린 것과 같다.
                         실행: python app.py --full-interview
  from_profile_file()  — main.py 가 이미 저장한 JSON(output/student_profile.json)을 그대로 읽는다. 대화 없음.
                         실행: python app.py --profile user_analysis/output/student_profile.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# user_analysis 모듈들은 `from schemas import ...` 처럼 서로를 평면 import 한다 (원작자가 그 폴더 안에서 실행).
# 파일을 고치지 않고 그대로 쓰기 위해 그 폴더를 import 경로에 넣는다.
_UA = Path(__file__).resolve().parent / "user_analysis"
if str(_UA) not in sys.path:
    sys.path.insert(0, str(_UA))

from profile_config import PROFILE_AREAS                              # noqa: E402  (고정 질문)
from profile_parser import analyze_area_answer, analyze_introduction  # noqa: E402  (LLM 분석 체인)
from profile_manager import get_missing_areas, is_profile_complete, update_profile  # noqa: E402
from question_agent import generate_next_question                    # noqa: E402  (main.py 의 적응형 질문)
from schemas import StudentProfileAnalysis                            # noqa: E402

from vocab import TRAIT_TO_SKILL, canonicalize

AREAS = ["interest", "strength"]          # 우리 그래프가 받을 수 있는 두 영역만 (interview() 용)
TRAIT_WEIGHT = 0.5                        # 성향에서 추정한 태그의 신뢰 가중치
TRAIT_MIN_CONFIDENCE = 0.6                # 이보다 낮은 confidence 의 성향은 쓰지 않는다
FULL_INTERVIEW_MAX_PER_AREA = 2           # main.py 의 question_counts[area] < 2 와 동일

INTRO_PROMPT = ("안녕! 전공이나 진로를 추천하기 전에 너에 대해 먼저 알고 싶어.\n"
                "좋아하는 것, 잘하는 것, 해본 것 등 편하게 자기소개해 줘.")


def profile_to_inputs(profile: StudentProfileAnalysis, intro: str | None = None,
                       extra_texts: list[str] | None = None) -> dict:
    """StudentProfileAnalysis(대화로 만들었든, 저장된 JSON 을 읽었든) → run() 이 받는 입력.

    interest.evidence 와 strength.mapped_traits 만 본다 — 나머지 5개 영역은 매칭 근거가 없어
    (약점을 부적합으로 안 쓴다는 user_analysis 규칙 14와 같은 이유로) 쓰지 않는다.
    intro/extra_texts 는 실시간 대화에서만 있는 원문 — 파일에서 읽었을 땐 None 으로 둬도 된다
    (그때는 leftover 나 interest.evidence 로 Q1 텍스트를 채운다).
    """
    interest, strength = profile.interest, profile.strength

    # ── 관심사: 사전 직행. LLM 이 정리한 분야·활동("데이터 분석", "통계")은 대개 우리 어휘 그대로라 조회만으로 태그가 된다.
    #    사전에 없는 것(미술, 게임…)만 태거로 넘긴다. 근거는 팀원 모듈이 적어 준 interest.evidence.
    interest_tags: list[str] = []
    interest_evidence: dict[str, str] = {}
    leftover: list[str] = []
    for item in list(interest.domains) + list(interest.activities):
        canon = canonicalize(item, strict=True)
        if canon and canon not in interest_tags:
            interest_tags.append(canon)
            interest_evidence[canon] = f"{item} ← \"{interest.evidence}\""
        elif not canon:
            leftover.append(item)

    # Q1 용 텍스트: 자기소개 원문(있으면) + 사전에 없던 표현. 둘 다 없으면 evidence 문장이라도 넘긴다.
    q1_text = " / ".join(([intro] if intro else []) + leftover) or interest.evidence or ""
    # Q2 용 텍스트: 강점 요약 + (실시간 대화라면) 추가 답변들
    q2_text = " / ".join([strength.summary] + (extra_texts or []))

    # ── 강점 성향: confidence 문턱 이상, direction=strength 만. 약점은 쓰지 않는다 (user_analysis 규칙 14)
    strong = [t for t in strength.mapped_traits
              if t.direction == "strength" and t.confidence >= TRAIT_MIN_CONFIDENCE]
    soft_traits = [t.trait for t in strong]                              # → 직무 요구 태도 대조 (graph_store)
    # 성향 → 기술 역량 (연관 관계, 0.5)
    trait_tags: list[str] = []
    trait_evidence: dict[str, str] = {}
    for t in strong:
        if t.trait in TRAIT_TO_SKILL and TRAIT_TO_SKILL[t.trait] not in trait_tags:
            trait_tags.append(TRAIT_TO_SKILL[t.trait])
            trait_evidence[TRAIT_TO_SKILL[t.trait]] = f"{t.trait} ← \"{t.evidence}\""

    return {"answers": [q1_text, q2_text],
            "interest_tags": interest_tags, "interest_evidence": interest_evidence,
            "trait_tags": trait_tags, "trait_evidence": trait_evidence,
            "soft_traits": soft_traits, "trait_details": {t.trait: t.evidence for t in strong},
            "profile": profile}


def interview(ask=input, say=print) -> dict:
    """자기소개 + 부족한 영역(최대 2개, 고정 질문) → profile_to_inputs() 결과.

    ask/say 를 주입할 수 있게 해 둔 이유: check.py 가 대본으로 자동 실행할 수 있어야 한다 (평가셋).
    """
    say(f"\n{INTRO_PROMPT}")
    intro = ask("> ")
    profile = analyze_introduction(intro)                              # LLM 1회 — 7개 영역 판정
    extra: list[str] = []

    for area in AREAS:                                                 # 부족한 영역만, 고정 질문으로 1회
        if not getattr(profile, area).sufficient:
            q = PROFILE_AREAS[area]["main_question"]
            say(f"\n{q}")
            ans = ask("> ")
            extra.append(ans)
            profile = update_profile(profile, area, analyze_area_answer(area, ans))   # LLM 1회

    result = profile_to_inputs(profile, intro=intro, extra_texts=extra)
    result["llm_calls"] = 1 + len(extra)
    return result


def _format_conversation(history: list[dict[str, str]]) -> str:
    """user_analysis/main.py 의 format_conversation() 과 동일 — 대화 기록을 LLM이 읽는 문자열로."""
    return "\n".join(f"{'학생' if h['role'] == 'student' else 'AI'}: {h['content']}" for h in history)


def full_interview(ask=input, say=print) -> dict:
    """user_analysis/main.py 와 완전히 같은 흐름 — question_agent 가 7개 영역을 전부 그때그때 물어본다.

    interview() 보다 LLM 호출이 훨씬 많다(매 라운드 질문 생성 1회 + 영역 분석 1회). 데모용 지름길이 아니라
    "app.py 에서 바로 main.py 를 돌린 것"이 필요할 때 쓴다. 완성된 프로필을 넘기는 순간까지는
    user_analysis 원본 함수(generate_next_question/update_profile/...)를 그대로 호출할 뿐이다.
    """
    say(f"\n{INTRO_PROMPT}")
    intro = ask("> ")
    profile = analyze_introduction(intro)
    history: list[dict[str, str]] = [{"role": "student", "content": intro}]
    extra: list[str] = []
    counts = {area: 0 for area in PROFILE_AREAS}

    while not is_profile_complete(profile):
        available = [a for a in get_missing_areas(profile) if counts[a] < FULL_INTERVIEW_MAX_PER_AREA]
        if not available:                                              # 더 물어볼 수 있는 영역이 없으면 종료
            break

        q = generate_next_question(missing_areas=available, conversation=_format_conversation(history))
        counts[q.area] += 1
        say(f"\n{q.question}")
        ans = ask("> ")
        history += [{"role": "assistant", "content": q.question}, {"role": "student", "content": ans}]
        extra.append(ans)
        profile = update_profile(profile, q.area, analyze_area_answer(q.area, ans))

    result = profile_to_inputs(profile, intro=intro, extra_texts=extra)
    result["llm_calls"] = 1 + sum(counts.values())
    return result


def load_profile(path: str | Path) -> StudentProfileAnalysis:
    """main.py 가 저장한 JSON(기본 output/student_profile.json, 같은 스키마면 어디서 받은 파일이든)을 읽는다."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return StudentProfileAnalysis.model_validate(data)


def from_profile_file(path: str | Path) -> dict:
    """저장된 프로필 JSON → profile_to_inputs() 결과. 대화 없이 파일 하나로 바로 끝난다."""
    return profile_to_inputs(load_profile(path))
