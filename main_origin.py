# schemas.py

from pydantic import BaseModel, Field
from typing import Literal


class MappedTrait(BaseModel):
    trait: str = Field(
        description="STANDARD_TRAITS 중 하나"
    )

    direction: Literal[
        "strength",
        "weakness",
        "neutral"
    ]

    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    evidence: str


class AreaResult(BaseModel):
    sufficient: bool
    summary: str
    mapped_traits: list[MappedTrait] = Field(
        default_factory=list
    )

class InterestResult(BaseModel):
    sufficient: bool

    domains: list[str] = Field(
        default_factory=list
    )

    activities: list[str] = Field(
        default_factory=list
    )

    evidence: str


class StudentProfileAnalysis(BaseModel):
    interest: InterestResult

    study_style: AreaResult

    strength: AreaResult

    weakness: AreaResult

    life_pattern: AreaResult

    social_style: AreaResult

    values: AreaResult


# profile_agent.py
# from langchain_openai import ChatOpenAI

# from schemas import StudentProfileAnalysis


# llm = ChatOpenAI(
#     model="gpt-4o-mini",
#     temperature=0
# )


# structured_llm = llm.with_structured_output(
#     StudentProfileAnalysis
# )

# prompts.py

from vocabulary import STANDARD_TRAITS, MAPPING_RULES


TRAIT_LIST_TEXT = "\n".join(
    f"- {trait}" for trait in STANDARD_TRAITS
)


SYSTEM_PROMPT = f"""
당신은 고등학생의 진로 탐색을 돕는 대화형 학생 프로필 분석 AI입니다.

목표:
학생의 자기소개와 대화를 통해 다음 7개 영역의 정보를 수집하고,
자연어 답변을 구조화된 학생 프로필로 변환합니다.

7개 영역:
1. interest: 관심사
2. study_style: 공부 스타일
3. strength: 강점
4. weakness: 약점
5. life_pattern: 생활 패턴
6. social_style: 친구 관계 / 모둠 활동
7. values: 성격 / 가치관

분석 규칙:
- 성향/역량 매핑에는 아래 STANDARD_TRAITS만 사용하세요.
- 학생이 직접 말한 내용에 근거하고 임의로 추론하지 마세요.
- 관심사와 능력을 구분하세요.
- 현재 단계에서는 학과, 과목, 직무를 추천하지 마세요.

STANDARD_TRAITS:
{TRAIT_LIST_TEXT}

{MAPPING_RULES}

대화 규칙:
- 먼저 학생이 자유롭게 자기소개하도록 합니다.
- 자기소개에서 충분히 확인된 영역은 다시 질문하지 않습니다.
- 부족한 영역만 추가 질문합니다.
- 한 번에 하나의 질문만 합니다.
- 답변이 불충분하거나 모호한 경우 해당 영역에 추가 질문을 최대 1회 합니다.
- 고등학생이 이해하기 쉬운 자연스러운 표현을 사용합니다.
"""

AREA_ANALYSIS_PROMPT = """
다음 학생의 답변을 분석하세요.

분석 대상 영역:
{area}

학생 답변:
{answer}

해야 할 일:

1. 해당 영역에 대한 정보가 충분한지 판단하세요.

2. 학생 답변의 핵심 의미를 짧게 요약하세요.

3. 표준 키워드가 명확히 드러나는 경우에만
   STANDARD_TRAITS 중 최대 3개를 선택하세요.

4. 각 키워드마다
   - strength
   - weakness
   - neutral
   중 하나를 지정하세요.

5. 각 판단에 대한 confidence를 0~1로 평가하세요.

6. 판단 근거가 된 학생의 표현을 evidence에 작성하세요.

7. 근거가 부족한 경우 mapped_traits를 빈 리스트로 반환하세요.
"""

INTRODUCTION_ANALYSIS_PROMPT = """
다음은 고등학생의 자유로운 자기소개입니다.

학생 자기소개:
{introduction}


자기소개에서 다음 7개 영역의 정보를 분석하세요.

1. interest: 관심사
2. study_style: 공부 스타일
3. strength: 강점
4. weakness: 약점
5. life_pattern: 생활 패턴
6. social_style: 친구 관계 / 모둠 활동
7. values: 성격 / 가치관


[공통 판단]

각 영역에 대해 해당 영역을 판단하기에
정보가 충분하면 sufficient=True,
부족하면 sufficient=False로 반환하세요.

학생이 직접 말한 내용만 근거로 사용하고,
학생이 말하지 않은 특성은 추측하지 마세요.


[interest 분석]

관심사는 다음 정보를 추출하세요.

- sufficient: 관심사를 파악하기에 정보가 충분한지
- domains: 관심을 보이는 분야
- activities: 해당 분야에서 좋아하는 활동
- evidence: 판단 근거가 된 학생의 발화

관심과 능력을 혼동하지 마세요.

예:
"그림은 잘 못 그리지만 미술관 가는 것을 좋아해요."

→ 미술에 대한 관심은 확인 가능
→ 창의성이나 미술 능력이 높다고 판단하지 않음


[나머지 6개 영역 분석]

study_style, strength, weakness,
life_pattern, social_style, values에 대해서는:

- sufficient: 해당 영역의 정보가 충분한지
- summary: 확인된 학생 특성을 간단히 요약
- mapped_traits: STANDARD_TRAITS에서 관련된 키워드 최대 3개

각 mapped_trait에는 다음 정보를 포함하세요.

- trait: STANDARD_TRAITS 중 하나
- direction: strength / weakness / neutral 중 하나
- confidence: 판단 신뢰도 0~1
- evidence: 해당 키워드를 판단한 학생 발화 근거


[주의사항]

- STANDARD_TRAITS에 없는 성향/역량 키워드를 임의로 생성하지 마세요.
- 근거가 부족하면 mapped_traits는 빈 리스트로 반환하세요.
- 친구 수를 협력성이나 사회성으로 판단하지 마세요.
- 내향적이라는 이유만으로 발표력, 설득력, 협력성이 낮다고 판단하지 마세요.
- 생활이 불규칙하다는 이유만으로 변화적응이 높거나 교대근무에 적합하다고 판단하지 마세요.
- 약점을 특정 학과나 직무의 부적합으로 판단하지 마세요.
- 현재 단계에서는 학과, 과목, 직무를 추천하지 마세요.
"""

AREA_ANALYSIS_PROMPT = """
현재 분석할 영역:

{area}


학생 답변:

{answer}


학생의 답변을 분석하세요.

규칙:

1. 현재 영역에 대한 정보가 충분한지 판단하세요.

2. 답변의 핵심 내용을 summary로 작성하세요.

3. STANDARD_TRAITS에 있는 키워드만 사용하세요.

4. 관련된 표준 키워드는 최대 3개만 선택하세요.

5. 각 키워드에 대해 다음을 판단하세요.

- trait
- direction
- confidence
- evidence

6. direction은 다음 중 하나입니다.

strength
weakness
neutral

7. 학생이 직접 말하지 않은 내용은 추론하지 마세요.

8. 근거가 부족한 경우 mapped_traits는 빈 리스트로 반환하세요.
"""

INTEREST_ANALYSIS_PROMPT = """
다음 학생의 답변에서 관심사를 분석하세요.

학생 답변:

{answer}


다음을 추출하세요.

1. sufficient
   학생의 관심사를 파악할 수 있을 정도로 정보가 충분한지

2. domains
   학생이 관심을 가지는 분야

3. activities
   해당 분야에서 학생이 좋아하는 활동

4. evidence
   판단 근거


주의:

좋아하는 것과 잘하는 것을 구분하세요.

예:

"그림 그리는 건 못하지만 미술관 가는 걸 좋아한다"

→ domains: ["미술", "문화예술"]

→ activities: ["미술 작품 감상"]

→ 창의성이 높다고 추론하지 않습니다.
"""

# vocabulary.py

STANDARD_TRAITS = {
    "분석성": {
        "category": "cognitive",
        "description": "정보를 나누고 원인이나 패턴을 파악하는 성향"
    },

    "논리성": {
        "category": "cognitive",
        "description": "근거와 순서를 바탕으로 판단하는 성향"
    },

    "문제해결": {
        "category": "cognitive",
        "description": "문제가 발생했을 때 해결 방법을 찾아 적용하는 능력"
    },

    "탐구성": {
        "category": "cognitive",
        "description": "궁금한 내용을 깊게 알아보려는 성향"
    },

    "창의성": {
        "category": "cognitive",
        "description": "새로운 아이디어나 방법을 만들어내는 성향"
    },

    "수리적사고": {
        "category": "cognitive",
        "description": "숫자, 계산, 패턴을 이해하고 활용하는 능력"
    },

    "언어표현": {
        "category": "communication",
        "description": "생각을 말이나 글로 명확하게 표현하는 능력"
    },

    "설득력": {
        "category": "communication",
        "description": "자신의 생각을 근거와 함께 전달해 상대방을 이해시키는 능력"
    },

    "발표력": {
        "category": "communication",
        "description": "여러 사람 앞에서 내용을 전달하는 능력"
    },

    "경청": {
        "category": "social",
        "description": "다른 사람의 의견과 이야기를 잘 듣는 성향"
    },

    "공감": {
        "category": "social",
        "description": "다른 사람의 감정이나 입장을 이해하는 성향"
    },

    "조정능력": {
        "category": "social",
        "description": "여러 사람의 의견이나 갈등을 정리하고 조율하는 능력"
    },

    "주도성": {
        "category": "social",
        "description": "먼저 행동하거나 방향을 제시하는 성향"
    },

    "협력성": {
        "category": "social",
        "description": "다른 사람과 함께 목표를 수행하는 성향"
    },

    "독립성": {
        "category": "work_style",
        "description": "혼자서 스스로 과제를 수행하는 것을 선호하는 성향"
    },

    "계획성": {
        "category": "work_style",
        "description": "일을 미리 정리하고 순서에 따라 진행하는 성향"
    },

    "지속성": {
        "category": "work_style",
        "description": "한 활동을 꾸준히 이어가는 성향"
    },

    "집중력": {
        "category": "work_style",
        "description": "한 활동에 몰입하고 주의를 유지하는 능력"
    },

    "실행력": {
        "category": "work_style",
        "description": "생각한 것을 실제 행동으로 옮기는 성향"
    },

    "정확성": {
        "category": "work_style",
        "description": "실수를 줄이고 꼼꼼하게 처리하려는 성향"
    },

    "변화적응": {
        "category": "work_style",
        "description": "새로운 환경이나 일정 변화에 적응하는 성향"
    },

    "도전성": {
        "category": "value",
        "description": "익숙하지 않은 일이나 새로운 일을 시도하려는 성향"
    },

    "자율성": {
        "category": "value",
        "description": "스스로 결정하고 수행하는 것을 선호하는 성향"
    },

    "안정지향": {
        "category": "value",
        "description": "예측 가능하고 안정적인 환경을 중요하게 생각하는 성향"
    },

    "성장지향": {
        "category": "value",
        "description": "새로운 것을 배우고 발전하는 것을 중요하게 생각하는 성향"
    },

    "성취지향": {
        "category": "value",
        "description": "목표 달성과 결과를 중요하게 생각하는 성향"
    },

    "사회기여": {
        "category": "value",
        "description": "다른 사람이나 사회에 도움이 되는 것을 중요하게 생각하는 성향"
    },

    "관계지향": {
        "category": "value",
        "description": "다른 사람들과 연결되고 함께하는 것을 중요하게 생각하는 성향"
    },

    "경쟁지향": {
        "category": "value",
        "description": "경쟁 상황에서 동기부여를 받는 성향"
    },

    "활동성": {
        "category": "work_style",
        "description": "몸을 움직이거나 외부 활동을 선호하는 성향"
    }
}

# from vocabulary import STANDARD_TRAITS

# trait_names = list(STANDARD_TRAITS.keys())

# print(trait_names)

MAPPING_RULES = """
학생의 답변을 분석하여 STANDARD_TRAITS 중 적절한 키워드만 선택하세요.

매핑 규칙:

1. 학생이 실제로 말한 내용에 근거해서만 판단합니다.

2. 관심과 능력을 구분합니다.
   예:
   "미술 전시 보는 것을 좋아한다"
   → 미술에 대한 관심은 확인 가능
   → 창의성이나 미술 능력이 높다고 판단하지 않습니다.

3. 하나의 답변에서 표준 키워드는 최대 3개까지만 선택합니다.

4. STANDARD_TRAITS에 없는 새로운 키워드를 만들지 않습니다.

5. 의미가 비슷한 표현은 가장 가까운 표준 키워드로 정규화합니다.
   예:
   "꼼꼼하다"
   → 정확성

   "친구들 의견을 정리한다"
   → 조정능력

   "새로운 것을 계속 찾아본다"
   → 탐구성

6. 답변에서 충분한 근거를 찾을 수 없으면
   키워드를 선택하지 않아도 됩니다.

7. 단순 자기평가보다 실제 행동 사례를 더 강한 근거로 사용합니다.
   예:
   "리더십이 있는 것 같다"
   보다
   "모둠활동에서 역할을 나누고 친구들을 이끈다"
   를 더 강한 근거로 사용합니다.

8. 강점과 약점을 구분합니다.

   strength:
   해당 특성이 학생의 강점으로 나타남

   weakness:
   해당 특성이 부족하거나 부담 요소로 나타남

   neutral:
   단순한 성향 또는 선호로 나타남

9. 서로 상충되는 정보가 있다면
   한쪽 정보를 임의로 제거하지 않습니다.
   대신 confidence를 낮춥니다.

10. 하나의 답변에서 과도하게 많은 성향을 추론하지 않습니다.

11. 친구 수와 협력성을 동일하게 판단하지 않습니다.

12. 생활이 불규칙하다는 이유만으로
    변화적응이 높다고 판단하지 않습니다.

13. 내향적이라는 이유만으로
    발표력, 설득력, 협력성이 낮다고 판단하지 않습니다.

14. 약점은 직무 부적합으로 직접 판단하지 않습니다.
    현재 단계에서는 학생의 특성만 추출합니다.
"""

# profile_parser.py

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from schemas import (
    StudentProfileAnalysis,
    AreaResult,
    InterestResult
)

from prompts import (
    SYSTEM_PROMPT,
    INTRODUCTION_ANALYSIS_PROMPT,
    AREA_ANALYSIS_PROMPT,
    INTEREST_ANALYSIS_PROMPT
)


# =========================================
# 1. 환경변수 로드
# =========================================

load_dotenv()


# =========================================
# 2. LLM 생성
# =========================================

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


# =========================================
# 3. 최초 자기소개 분석 Chain
# =========================================

intro_structured_llm = llm.with_structured_output(
    StudentProfileAnalysis
)


intro_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", INTRODUCTION_ANALYSIS_PROMPT)
])


intro_chain = intro_prompt | intro_structured_llm


# =========================================
# 4. 일반 영역 추가답변 분석 Chain
# =========================================

area_structured_llm = llm.with_structured_output(
    AreaResult
)


area_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", AREA_ANALYSIS_PROMPT)
])


area_chain = area_prompt | area_structured_llm


# =========================================
# 5. 관심사 추가답변 분석 Chain
# =========================================

interest_structured_llm = llm.with_structured_output(
    InterestResult
)


interest_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", INTEREST_ANALYSIS_PROMPT)
])


interest_chain = interest_prompt | interest_structured_llm


# =========================================
# 6. 최초 자기소개 분석 함수
# =========================================

def analyze_introduction(
    introduction: str
) -> StudentProfileAnalysis:

    result = intro_chain.invoke({
        "introduction": introduction
    })

    return result


# =========================================
# 7. 추가 질문 답변 분석 함수
# =========================================

def analyze_area_answer(
    area: str,
    answer: str
):

    # 관심사는 InterestResult 구조 사용
    if area == "interest":

        result = interest_chain.invoke({
            "answer": answer
        })

    # 나머지 6개 영역은 AreaResult 구조 사용
    else:

        result = area_chain.invoke({
            "area": area,
            "answer": answer
        })

    return result

# profile_config.py

PROFILE_AREAS = {
    "interest": {
        "name": "관심사",
        "purpose": (
            "학생이 잘하고 못하는 것과 관계없이 "
            "진짜 흥미와 재미를 느끼는 분야나 활동을 파악한다."
        ),
        "main_question": (
            "요즘 시간 가는 줄 모르고 관심을 갖거나 "
            "재미있게 보는 분야나 활동이 있어?"
        ),
        "follow_up_question": (
            "그걸 좋아하는 이유가 뭐야? "
            "직접 해보는 게 좋은지, 보는 게 좋은지, "
            "알아가는 과정이 좋은지도 이야기해줄래?"
        ),
    },

    "study_style": {
        "name": "공부 스타일",
        "purpose": (
            "학생이 새로운 내용을 배울 때 어떤 방식으로 "
            "집중하고 이해하는지 파악한다."
        ),
        "main_question": (
            "공부하거나 새로운 걸 배울 때 "
            "어떤 방식이 제일 잘 맞는 것 같아?"
        ),
        "follow_up_question": (
            "예를 들어 혼자 오래 집중하는 편인지, "
            "짧게 집중하는 편인지, 직접 해보거나 "
            "말하면서 배우는 편인지 등 알려줄래?"
        ),
    },

    "strength": {
        "name": "강점",
        "purpose": (
            "학생이 실제로 잘하거나 주변 사람들에게 "
            "잘한다고 평가받는 능력과 행동 특성을 파악한다."
        ),
        "main_question": (
            "학교생활이나 평소 생활에서 "
            "내가 이것만큼은 잘한다고 생각하는 게 있어?"
        ),
        "follow_up_question": (
            "친구나 가족, 선생님한테 자주 칭찬받는 부분도 있을까?"
        ),
    },

    "weakness": {
        "name": "약점",
        "purpose": (
            "학생이 지속적으로 어렵다고 느끼거나 "
            "부담을 느끼는 활동이나 환경을 파악한다."
        ),
        "main_question": (
            "반대로 내가 유독 어렵거나 자신 없다고 느끼는 건 뭐가 있어?"
        ),
        "follow_up_question": (
            "그 상황을 만나면 보통 피하고 싶은 편인지, "
            "해보긴 하지만 많이 힘든 편인지도 알려줄래?"
        ),
    },

    "life_pattern": {
        "name": "생활 패턴",
        "purpose": (
            "학생이 편하게 느끼는 활동 시간, 일정, 이동, "
            "환경 변화 등의 생활 패턴을 파악한다."
        ),
        "main_question": (
            "평소 생활 패턴은 어떤 편이야? "
            "규칙적인 편인지 그날그날 다른 편인지 궁금해."
        ),
        "follow_up_question": (
            "아침이나 밤 중 언제 더 집중이 잘 되고, "
            "새로운 장소나 일정 변화에는 잘 적응하는 편이야?"
        ),
    },

    "social_style": {
        "name": "친구 관계 / 모둠 활동",
        "purpose": (
            "친구나 모둠 속에서 학생이 어떤 역할을 하고 "
            "사람들과 어떤 방식으로 상호작용하는지 파악한다."
        ),
        "main_question": (
            "친구들이랑 같이 무언가 할 때 "
            "보통 어떤 역할을 맡는 편이야?"
        ),
        "follow_up_question": (
            "예를 들어 의견을 내는 편인지, "
            "친구들 이야기를 듣는 편인지, "
            "정리하거나 이끄는 편인지 알려줄래?"
        ),
    },

    "values": {
        "name": "성격 / 가치관",
        "purpose": (
            "학생이 중요하게 생각하는 가치와 "
            "전반적인 행동 성향을 파악한다."
        ),
        "main_question": (
            "뭔가를 선택할 때 너한테 가장 중요한 건 뭐야?"
        ),
        "follow_up_question": (
            "예를 들어 안정적인 것, 새로운 도전, "
            "성장하는 것, 인정받는 것, 다른 사람에게 도움을 주는 것 중 "
            "어떤 게 더 중요해?"
        ),
    },
}

# {
#     "interest": True,
#     "study_style": True,
#     "strength": True,
#     "weakness": False,
#     "life_pattern": False,
#     "social_style": True,
#     "values": False
# }
# 다음 질문은 
# weakness
# life_pattern
# values

# question_agent.py

from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from dotenv import load_dotenv


load_dotenv()


# =========================================
# 질문 결과 Schema
# =========================================

class QuestionResult(BaseModel):

    area: str = Field(
        description="이번 질문에서 확인할 영역"
    )

    question: str = Field(
        description="학생에게 실제로 보여줄 자연스러운 질문"
    )


# =========================================
# LLM
# =========================================

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3
)


question_llm = llm.with_structured_output(
    QuestionResult
)


# =========================================
# Prompt
# =========================================

QUESTION_PROMPT = """
당신은 고등학생을 대상으로 진로 탐색 대화를 진행합니다.

아직 정보가 부족한 영역은 다음과 같습니다.

{missing_areas}


현재까지 학생과 나눈 대화:

{conversation}


해야 할 일:

1. missing_areas 중 현재 대화 흐름에서
   가장 자연스럽게 물어볼 영역 하나를 선택하세요.

2. 학생이 부담 없이 대답할 수 있는 질문 하나를 만드세요.

3. 한 번에 여러 질문을 하지 마세요.

4. 학과나 직업을 추천하지 마세요.

5. 학생에게 전문적인 표현을 사용하지 마세요.

6. 이미 대화에서 충분히 확인한 내용을 다시 묻지 마세요.

영역 의미:

interest:
학생이 좋아하고 흥미를 느끼는 분야나 활동

study_style:
학생이 어떤 방식으로 공부하거나 배우는 것을 편하게 느끼는지

strength:
학생이 자신 있게 잘한다고 느끼는 것

weakness:
학생이 어렵거나 부담스럽게 느끼는 것

life_pattern:
일정 변화, 활동 시간, 생활 환경 등에 대한 선호

social_style:
친구 또는 모둠 활동에서 주로 보이는 행동

values:
학생이 선택할 때 중요하게 생각하는 가치나 성향
"""


question_prompt = ChatPromptTemplate.from_messages([
    ("system", "학생의 진로 프로필을 수집하는 대화형 상담 AI입니다."),
    ("human", QUESTION_PROMPT)
])


question_chain = question_prompt | question_llm


# =========================================
# 질문 생성 함수
# =========================================

def generate_next_question(
    missing_areas: list[str],
    conversation: str
) -> QuestionResult:

    result = question_chain.invoke({
        "missing_areas": ", ".join(missing_areas),
        "conversation": conversation
    })


    # 혹시 LLM이 missing 영역이 아닌 것을 고른 경우
    if result.area not in missing_areas:

        result.area = missing_areas[0]

    return result

# profile_manager.py

import json
import os

from schemas import StudentProfileAnalysis


# =========================================
# 부족한 영역 찾기
# =========================================

def get_missing_areas(
    profile: StudentProfileAnalysis
) -> list[str]:

    missing_areas = []

    profile_dict = profile.model_dump()

    for area_name, area_data in profile_dict.items():

        if area_data["sufficient"] is False:
            missing_areas.append(area_name)

    return missing_areas


# =========================================
# 새로운 답변으로 프로필 업데이트
# =========================================

def update_profile(
    profile: StudentProfileAnalysis,
    area: str,
    new_result
) -> StudentProfileAnalysis:

    updated_profile = profile.model_copy(
        update={
            area: new_result
        }
    )

    return updated_profile


# =========================================
# 프로필 완성 여부 확인
# =========================================

def is_profile_complete(
    profile: StudentProfileAnalysis
) -> bool:

    missing_areas = get_missing_areas(profile)

    return len(missing_areas) == 0


# =========================================
# 최종 JSON 저장
# =========================================

def save_profile(
    profile: StudentProfileAnalysis,
    file_path="output/student_profile.json"
):

    os.makedirs(
        os.path.dirname(file_path),
        exist_ok=True
    )

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            profile.model_dump(),
            f,
            ensure_ascii=False,
            indent=4
        )

# main.py

from profile_parser import (
    analyze_introduction,
    analyze_area_answer
)

from question_agent import (
    generate_next_question
)

from profile_manager import (
    get_missing_areas,
    update_profile,
    is_profile_complete,
    save_profile
)


def format_conversation(history):
    """
    대화 기록을 LLM이 읽기 쉬운 문자열로 변환
    """

    lines = []

    for message in history:

        if message["role"] == "student":
            speaker = "학생"

        else:
            speaker = "AI"

        lines.append(
            f"{speaker}: {message['content']}"
        )

    return "\n".join(lines)


def main():

    # -----------------------------------------
    # 1. 대화 기록
    # -----------------------------------------

    conversation_history = []


    # -----------------------------------------
    # 2. 영역별 질문 횟수 기록
    # -----------------------------------------

    question_counts = {
        "interest": 0,
        "study_style": 0,
        "strength": 0,
        "weakness": 0,
        "life_pattern": 0,
        "social_style": 0,
        "values": 0
    }


    # -----------------------------------------
    # 3. 최초 안내
    # -----------------------------------------

    print("\n안녕하세요!")
    print("진로나 전공을 추천하기 전에 먼저 당신에 대해 알아보고 싶어요.")
    print("좋아하는 것, 공부 방식, 학교생활 등 편하게 자기소개해 주세요.\n")


    # -----------------------------------------
    # 4. 학생 자기소개 입력
    # -----------------------------------------

    introduction = input("학생: ")


    conversation_history.append({
        "role": "student",
        "content": introduction
    })


    # -----------------------------------------
    # 5. 자기소개 분석
    # -----------------------------------------

    profile = analyze_introduction(
        introduction
    )


    # -----------------------------------------
    # 6. 부족한 영역이 있는 동안 반복
    # -----------------------------------------

    while not is_profile_complete(profile):


        # 현재 부족한 영역 찾기
        missing_areas = get_missing_areas(
            profile
        )


        # 질문을 2번 미만으로 한 영역만 남기기
        available_areas = [
            area
            for area in missing_areas
            if question_counts[area] < 2
        ]


        # 더 이상 질문할 수 있는 영역이 없으면 종료
        if not available_areas:
            break


        # 지금까지 대화 문자열로 변환
        conversation_text = format_conversation(
            conversation_history
        )


        # -------------------------------------
        # 7. 다음 질문 생성
        # -------------------------------------

        question_result = generate_next_question(
            missing_areas=available_areas,
            conversation=conversation_text
        )


        area = question_result.area
        question = question_result.question


        question_counts[area] += 1


        # 질문 출력
        print(f"\nAI: {question}")


        conversation_history.append({
            "role": "assistant",
            "content": question
        })


        # -------------------------------------
        # 8. 학생 추가 답변 입력
        # -------------------------------------

        answer = input("학생: ")


        conversation_history.append({
            "role": "student",
            "content": answer
        })


        # -------------------------------------
        # 9. 추가 답변 분석
        # -------------------------------------

        new_result = analyze_area_answer(
            area=area,
            answer=answer
        )


        # -------------------------------------
        # 10. 기존 프로필 업데이트
        # -------------------------------------

        profile = update_profile(
            profile=profile,
            area=area,
            new_result=new_result
        )


    # -----------------------------------------
    # 11. 종료 후 결과 출력
    # -----------------------------------------

    print("\n==============================")
    print("학생 프로필 수집 완료")
    print("==============================\n")


    print(
        profile.model_dump_json(
            indent=2
        )
    )


    # -----------------------------------------
    # 12. JSON 저장
    # -----------------------------------------

    save_profile(profile)


    print(
        "\n학생 프로필을 "
        "output/student_profile.json에 저장했습니다."
    )


# ---------------------------------------------
# 프로그램 실행
# ---------------------------------------------

if __name__ == "__main__":
    main()