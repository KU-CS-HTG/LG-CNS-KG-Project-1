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

원본과 다른 점 두 가지 (데모 30초 · 재현성):
  - 질문은 LLM 이 만들지 않고 PROFILE_AREAS 의 고정 질문을 쓴다 (원본은 temperature=0.3 으로 생성 → 매번 다름)
  - 영역당 추가 질문 최대 1회. LLM 호출은 자기소개 분석 1 + 영역 분석 ≤2 = 최대 3회 (+ 태거 1회)

실행:  python app.py --interview
"""
from __future__ import annotations

import sys
from pathlib import Path

# user_analysis 모듈들은 `from schemas import ...` 처럼 서로를 평면 import 한다 (원작자가 그 폴더 안에서 실행).
# 파일을 고치지 않고 그대로 쓰기 위해 그 폴더를 import 경로에 넣는다.
_UA = Path(__file__).resolve().parent / "user_analysis"
if str(_UA) not in sys.path:
    sys.path.insert(0, str(_UA))

from profile_config import PROFILE_AREAS                              # noqa: E402  (고정 질문)
from profile_parser import analyze_area_answer, analyze_introduction  # noqa: E402  (LLM 분석 체인)
from profile_manager import update_profile                            # noqa: E402

from vocab import TRAIT_TO_SKILL, canonicalize

AREAS = ["interest", "strength"]          # 우리 그래프가 받을 수 있는 두 영역만
TRAIT_WEIGHT = 0.5                        # 성향에서 추정한 태그의 신뢰 가중치
TRAIT_MIN_CONFIDENCE = 0.6                # 이보다 낮은 confidence 의 성향은 쓰지 않는다

INTRO_PROMPT = ("안녕! 전공이나 진로를 추천하기 전에 너에 대해 먼저 알고 싶어.\n"
                "좋아하는 것, 잘하는 것, 해본 것 등 편하게 자기소개해 줘.")


def interview(ask=input, say=print) -> dict:
    """자기소개 + 부족한 영역 질문 → {"answers": [Q1용 텍스트, Q2용 텍스트], "trait_tags": [...], "profile": ...}

    ask/say 를 주입할 수 있게 해 둔 이유: check.py 가 대본으로 자동 실행할 수 있어야 한다 (평가셋).
    """
    say(f"\n{INTRO_PROMPT}")
    intro = ask("> ")
    profile = analyze_introduction(intro)                              # LLM 1회 — 7개 영역 판정
    transcript = [intro]

    for area in AREAS:                                                 # 부족한 영역만, 고정 질문으로 1회
        if not getattr(profile, area).sufficient:
            q = PROFILE_AREAS[area]["main_question"]
            say(f"\n{q}")
            ans = ask("> ")
            transcript.append(ans)
            profile = update_profile(profile, area, analyze_area_answer(area, ans))   # LLM 1회

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

    # Q1 용 텍스트: 자기소개 원문 + 사전에 없던 표현. (사전에서 잡힌 건 넣지 않는다 — 같은 걸 LLM 이 두 번 읽지 않게)
    q1_text = " / ".join([intro] + leftover)
    # Q2 용 텍스트: 강점 요약 + 추가 답변
    q2_text = " / ".join([strength.summary] + transcript[1:])

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
            "profile": profile, "llm_calls": 1 + (len(transcript) - 1)}
