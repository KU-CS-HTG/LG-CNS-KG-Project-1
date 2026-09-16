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