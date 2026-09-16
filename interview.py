"""interview.py — 대화형 입력 모드 (user_analysis 어댑터)

팀원이 만든 user_analysis/ (자기소개 → 7개 영역 프로필) 를 우리 파이프라인의 **입력 단계**로 붙인다.
user_analysis 의 파일은 건드리지 않는다. 이 파일이 둘 사이를 잇는 유일한 접점이다.

우리가 태그로 쓰는 것 (7개 영역 중 2개 + 성향 분류 1개):
  interest    → domains·activities 를 먼저 **사전(vocab.canonicalize)** 으로 태그화 (LLM 0, 근거 = interest.evidence)
                사전에 없는 표현(미술, 음악…)만 자기소개 원문과 함께 태거(app.normalize_to_tags)로   ← 효과의 대부분
  strength    → mapped_traits(direction=strength) →
                ① vocab.TRAIT_TO_SKILL → 기술 역량 태그 (가중치 0.5, 전공 매칭용)
                ② vocab.TRAIT_TO_SOFT  → 소프트 스킬 → 직무의 요구 태도(job.soft)와 대조 (동점 처리 전용)
  (전체 프로필) → infer_orientation() 이 "데이터 분석 / 시스템 설계 / 사람·일정 조율" 중 하나를 판단
                (예전엔 이걸 사용자에게 "① ② ③ 중 골라줘"로 따로 물었다 — 자연스러운 인터뷰 도중에
                갑자기 객관식이 끼어드는 게 어색해서, 이미 모은 프로필로 같은 판단을 LLM에게 대신 시킨다)
나머지 4개(생활·친구·가치관·공부 스타일)는 태그로는 안 쓰지만, [진로 추천] 문단을 쓸 때 배경 설명으로 쓴다
(profile_summary_text, explain()의 "[학생 프로필]" 절 — app.build_explain_prompt 참고). 약점은 태그에도
문단에도 근거로 쓰지 않는다 (user_analysis 규칙 14: 약점을 부적합 판단에 쓰지 않는다).

세 가지 방법으로 프로필(StudentProfileAnalysis)을 채울 수 있고, 채운 다음엔 전부
profile_to_inputs() 하나로 수렴한다 — 대화든 파일이든 run() 이 받는 모양은 같다.

  interview()         — 데모용. 질문은 LLM 이 만들지 않고 PROFILE_AREAS 의 고정 질문(2개 영역, 영역당 최대 1회)을 쓴다.
                         (원본은 temperature=0.3 으로 질문을 생성해 매번 달라진다) 실행: python app.py --interview
  full_interview()    — user_analysis/main.py 와 동일한 흐름. question_agent 가 7개 영역 전부를 그때그때
                         물어본다(영역당 최대 2회). LLM 호출이 더 많은 대신 main.py 를 직접 돌린 것과 같다.
                         app.py 의 기본값 (플래그 없이 python app.py 만 실행해도 이 흐름을 탄다).
                         옛 고정 3질문 모드가 필요하면 python app.py --basic.
  from_profile_file()  — main.py 가 이미 저장한 JSON(output/student_profile.json)을 그대로 읽는다. 대화 없음.
                         실행: python app.py --profile user_analysis/output/student_profile.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

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

# 영역 이름 → 문단/성향 판단에 쓸 한국어 라벨. interest 는 domains/activities 를 따로 다루므로 여기 없다.
# 약점(weakness)은 9/16 팀 결정으로 user_analysis 에서 영역 자체가 빠졌다 (묻지도, 프로필에 두지도 않는다).
_AREA_LABELS = {
    "study_style": "공부 스타일", "strength": "강점",
    "life_pattern": "생활 패턴", "social_style": "친구·모둠에서의 모습", "values": "중요하게 여기는 것",
}


def profile_summary_text(profile: StudentProfileAnalysis, include_weakness: bool = True) -> str:
    """프로필에서 정보가 충분한 영역만 한국어 줄글로. [진로 추천] 문단과 성향 판단에 같이 쓴다.

    include_weakness=False 로 부르면 약점 줄을 뺀다 — 성향(데이터/시스템/사람) 판단에는
    약점을 근거로 쓰지 않는다 (user_analysis 규칙 14와 같은 이유: 약점 → 부적합 판단 금지).

    getattr(..., None) 으로 읽는 이유: user_analysis/schemas.py 의 StudentProfileAnalysis 에서
    영역을 빼거나 이름을 바꿀 수 있다(예: weakness 질문을 아예 없앤 경우) — 그때 pydantic은
    없는 필드에 접근하면 AttributeError 를 던진다. 여기서는 있는 영역만 쓰고 없는 건 조용히 건너뛴다.
    """
    interest = profile.interest
    lines: list[str] = []
    if interest.sufficient and (interest.domains or interest.activities or interest.evidence):
        what = ", ".join(list(interest.domains) + list(interest.activities)) or interest.evidence
        lines.append(f"관심사: {what}")

    for area, label in _AREA_LABELS.items():
        if area == "weakness" and not include_weakness:
            continue
        data = getattr(profile, area, None)
        if data is not None and data.sufficient and data.summary:
            lines.append(f"{label}: {data.summary}")

    return "\n".join(lines)


class _OrientationResult(BaseModel):
    tag: Literal["Data Analysis", "Software Engineering", "Project Management"] | None = Field(
        default=None,
        description="학생 프로필에서 뚜렷하게 드러나는 성향 하나. 셋 다 뚜렷한 근거가 없으면 null.")
    evidence: str = Field(default="", description="판단 근거가 된 프로필 문장. tag 가 null 이면 빈 문자열.")


_ORIENTATION_SYSTEM = """당신은 고등학생의 진로 성향을 판단하는 상담 AI입니다.
아래 [학생 프로필]을 보고, 다음 세 가지 성향 중 학생에게 가장 가까운 것 하나를 고르세요.

- Data Analysis: 데이터를 파고들어 패턴을 찾는 것에 더 끌린다
- Software Engineering: 시스템을 설계하고 만드는 것에 더 끌린다
- Project Management: 사람과 일정을 조율해 프로젝트를 굴리는 것에 더 끌린다

규칙:
1. 프로필에 직접적인 근거가 있을 때만 고르세요. 셋 다 근거가 약하면 tag 를 null 로 반환하세요 — 어느 하나를
   무리해서 고르지 마세요.
2. "어려워하는 것"(약점)은 이 판단에 쓰지 마세요. 어렵다고 느끼는 것이 그 일을 못 한다는 뜻은 아닙니다.
3. evidence 에는 판단 근거가 된 프로필의 문장을 그대로 적으세요."""

_orientation_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
_orientation_prompt = ChatPromptTemplate.from_messages([
    ("system", _ORIENTATION_SYSTEM),
    ("human", "{profile_text}"),
])
_orientation_chain = _orientation_prompt | _orientation_llm.with_structured_output(_OrientationResult)


def infer_orientation(profile: StudentProfileAnalysis) -> tuple[str | None, str]:
    """"데이터 분석/시스템 설계/사람 조율" 중 하나를 프로필에서 판단. (태그, 근거) 를 돌려준다.

    예전 Q3("① ② ③ 중 골라줘")를 대신한다. 규칙 기반이 아니라 LLM 1회를 쓰는 이유: Q3 는 선택지가
    정해져 있어 규칙으로 풀 수 있었지만, 여기서는 "어느 문장이 어느 선택지에 해당하는가"부터 판단해야
    해서 규칙만으로는 안 된다. 대신 자유 서술 3문장이 아니라 **프로필 전체**(interest+strength+
    study_style+life_pattern+social_style+values)를 근거로 주기 때문에, 답 하나("2")만 주고 판단하게
    했던 예전 실패(2026-09-15 실측)보다 근거가 훨씬 두껍다.
    """
    text = profile_summary_text(profile, include_weakness=False)
    if not text.strip():
        return None, ""
    result = _orientation_chain.invoke({"profile_text": text})
    return result.tag, result.evidence


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

    # ── 성향 판단(예전 Q3 대신) — 사용자가 직접 답한 것과 같은 무게로 stated 쪽(interest_tags)에 얹는다.
    orientation_tag, orientation_evidence = infer_orientation(profile)
    if orientation_tag and orientation_tag not in interest_tags:
        interest_tags.append(orientation_tag)
        interest_evidence[orientation_tag] = orientation_evidence or "(전체 프로필에서 판단)"

    return {"answers": [q1_text, q2_text],
            "interest_tags": interest_tags, "interest_evidence": interest_evidence,
            "trait_tags": trait_tags, "trait_evidence": trait_evidence,
            "soft_traits": soft_traits, "trait_details": {t.trait: t.evidence for t in strong},
            "orientation_tag": orientation_tag, "orientation_evidence": orientation_evidence,
            "profile_summary": profile_summary_text(profile), "profile": profile}


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
    result["llm_calls"] = 1 + len(extra) + 1     # 자기소개 분석 + 영역 분석 + profile_to_inputs 의 infer_orientation()
    return result


def _format_conversation(history: list[dict[str, str]]) -> str:
    """user_analysis/main.py 의 format_conversation() 과 동일 — 대화 기록을 LLM이 읽는 문자열로."""
    return "\n".join(f"{'학생' if h['role'] == 'student' else 'AI'}: {h['content']}" for h in history)


class InterviewSession:
    """user_analysis/main.py 와 같은 흐름(7개 영역, 적응형 질문)을 **한 걸음씩** 진행한다.

    full_interview() 는 CLI 의 input()/print() 루프로 이걸 감싼 것뿐이다 — 로직은 여기 하나뿐이다.
    webapp.py 처럼 매 요청마다 한 걸음만 내딛고 상태를 어딘가에 들고 있어야 하는 곳(HTTP는 대화 중간에
    멈춰 있을 수 없다)에서는 이 클래스를 직접 쓴다: start() → answer() 를 다음 질문이 None 이 될 때까지
    반복하고, 끝나면 finish() 로 profile_to_inputs() 결과를 받는다.
    """

    def __init__(self) -> None:
        self.profile: StudentProfileAnalysis | None = None
        self.intro: str | None = None
        self.history: list[dict[str, str]] = []
        self.extra: list[str] = []
        self.counts: dict[str, int] = {area: 0 for area in PROFILE_AREAS}
        self._pending_area: str | None = None
        self._pending_question: str | None = None

    def start(self, intro: str) -> str | None:
        """자기소개 → 프로필 초기화(LLM 1회). 다음 질문을 돌려준다. 처음부터 다 채워졌으면 None."""
        self.intro = intro
        self.profile = analyze_introduction(intro)
        self.history = [{"role": "student", "content": intro}]
        return self._advance()

    def answer(self, text: str) -> str | None:
        """직전 질문에 대한 답 → 프로필 갱신(LLM 1회). 다음 질문을 돌려준다. 더 물을 게 없으면 None."""
        area = self._pending_area
        self.history += [{"role": "assistant", "content": self._pending_question},
                          {"role": "student", "content": text}]
        self.extra.append(text)
        self.profile = update_profile(self.profile, area, analyze_area_answer(area, text))
        return self._advance()

    def _advance(self) -> str | None:
        available = [a for a in get_missing_areas(self.profile) if self.counts[a] < FULL_INTERVIEW_MAX_PER_AREA]
        if is_profile_complete(self.profile) or not available:          # 더 물어볼 수 있는 영역이 없으면 종료
            self._pending_area = self._pending_question = None
            return None
        q = generate_next_question(missing_areas=available, conversation=_format_conversation(self.history))
        self.counts[q.area] += 1
        self._pending_area, self._pending_question = q.area, q.question
        return q.question

    def finish(self) -> dict:
        """profile_to_inputs() 결과. llm_calls 는 자기소개 분석 + 영역 분석 + infer_orientation() 합."""
        result = profile_to_inputs(self.profile, intro=self.intro, extra_texts=self.extra)
        result["llm_calls"] = 1 + sum(self.counts.values()) + 1
        return result


def full_interview(ask=input, say=print) -> dict:
    """user_analysis/main.py 와 완전히 같은 흐름 — question_agent 가 7개 영역을 전부 그때그때 물어본다.

    interview() 보다 LLM 호출이 훨씬 많다(매 라운드 질문 생성 1회 + 영역 분석 1회). 데모용 지름길이 아니라
    "app.py 에서 바로 main.py 를 돌린 것"이 필요할 때 쓴다. 실제 진행은 InterviewSession 이 한다 —
    이 함수는 그걸 input()/print() 루프로 감싼 CLI 용 얇은 래퍼.
    """
    say(f"\n{INTRO_PROMPT}")
    session = InterviewSession()
    q = session.start(ask("> "))
    while q is not None:
        say(f"\n{q}")
        q = session.answer(ask("> "))
    return session.finish()


def load_profile(path: str | Path) -> StudentProfileAnalysis:
    """main.py 가 저장한 JSON(기본 output/student_profile.json, 같은 스키마면 어디서 받은 파일이든)을 읽는다."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return StudentProfileAnalysis.model_validate(data)


def from_profile_file(path: str | Path) -> dict:
    """저장된 프로필 JSON → profile_to_inputs() 결과. 대화 없이 파일 하나로 바로 끝난다."""
    return profile_to_inputs(load_profile(path))
