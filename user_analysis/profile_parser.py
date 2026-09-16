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
