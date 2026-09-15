"""interview.py — 대화형 입력 모드 (user_analysis 어댑터)

팀원이 만든 user_analysis/ (자기소개 → 7개 영역 프로필) 를 우리 파이프라인의 **입력 단계**로 붙인다.
user_analysis 의 파일은 건드리지 않는다. 이 파일이 둘 사이를 잇는 유일한 접점이다.

우리가 쓰는 것 (7개 영역 중 2개):
  interest  → domains·activities 텍스트 → 그대로 태거(app.normalize_to_tags)에 넣는다      ← 효과의 대부분
  strength  → mapped_traits(direction=strength) → vocab.TRAIT_TO_SKILL → 태그 (가중치 0.5)   ← 보조
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

from vocab import TRAIT_TO_SKILL

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

    # Q1 용 텍스트: 자기소개 + 관심 분야·활동 (LLM 이 정리한 것) — 태거가 우리 어휘로 바꾼다
    q1_text = " / ".join([intro] + list(interest.domains) + list(interest.activities))
    # Q2 용 텍스트: 강점 요약 + 추가 답변
    q2_text = " / ".join([strength.summary] + transcript[1:])

    # 성향 → 역량 (연관 관계, 0.5). strength 로 판정된 성향만, confidence 문턱 이상만
    trait_tags: list[str] = []
    trait_evidence: dict[str, str] = {}
    for t in strength.mapped_traits:
        if t.direction == "strength" and t.confidence >= TRAIT_MIN_CONFIDENCE and t.trait in TRAIT_TO_SKILL:
            skill = TRAIT_TO_SKILL[t.trait]
            if skill not in trait_tags:
                trait_tags.append(skill)
                trait_evidence[skill] = f"{t.trait} ← \"{t.evidence}\""

    return {"answers": [q1_text, q2_text], "trait_tags": trait_tags,
            "trait_evidence": trait_evidence, "profile": profile, "llm_calls": 1 + (len(transcript) - 1)}
