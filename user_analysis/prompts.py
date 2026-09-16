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
- activities: 해당 분야에서 좋아하거나 실제로 하는 활동
- evidence: 판단 근거가 된 학생의 발화
- mapped_traits: 관심 분야 자체가 아닌, 관심과 관련된 구체적인 행동이나 경험에서 근거가 확인되는 STANDARD_TRAITS 성향

관심과 능력을 혼동하지 마세요.

예:

"그림은 잘 못 그리지만 미술관 가는 것을 좋아해요."

→ domains: ["미술"]
→ activities: ["미술 작품 감상"]
→ mapped_traits: []

미술에 대한 관심은 확인 가능하지만,
창의성이나 미술 능력이 높다고 판단하지 않음


"새로운 AI 기술이 나오면 궁금해서 직접 찾아보고 공부해요."

→ domains: ["AI", "기술"]
→ activities: ["새로운 AI 기술 탐색", "관련 내용 학습"]
→ mapped_traits: ["탐구성"]

단순히 AI에 관심이 있어서가 아니라,
'직접 찾아보고 공부한다'는 행동 근거가 있으므로 탐구성을 판단할 수 있음


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

INTEREST_ANALYSIS_PROMPT = f"""
다음 학생의 답변에서 관심사를 분석하세요.

학생 답변:

{{answer}}


다음을 추출하세요.

1. sufficient
   학생의 관심사를 파악할 수 있을 정도로 정보가 충분한지

2. domains
   학생이 관심을 가지는 분야

3. activities
   해당 분야에서 학생이 좋아하거나 실제로 하는 활동

4. evidence
   관심사를 판단한 근거가 되는 학생의 실제 발화

5. mapped_traits
   학생의 답변에서 STANDARD_TRAITS에 해당하는 성향이
   행동이나 경험을 통해 명확하게 드러난 경우에만 추출하세요.

   각 mapped_trait에는 다음 정보를 포함하세요.
   - trait: STANDARD_TRAITS 중 하나
   - direction: strength / weakness / neutral
   - confidence: 해당 발화가 그 trait을 나타낸다고 판단하는 신뢰도 (0.0~1.0)
   - evidence: 해당 trait을 판단한 학생의 실제 발화


사용 가능한 STANDARD_TRAITS:

{TRAIT_LIST_TEXT}


매핑 규칙:

{MAPPING_RULES}


주의:

좋아하는 것과 잘하는 것을 구분하세요.

관심 분야 자체만으로 학생의 성향이나 능력을 추론하지 마세요.

예를 들어:

"그림 그리는 건 못하지만 미술관 가는 걸 좋아한다"

→ domains: ["미술", "문화예술"]
→ activities: ["미술 작품 감상"]
→ mapped_traits: []

단순히 미술을 좋아한다는 이유만으로
창의성이 높다고 추론하지 않습니다.


반면:

"AI가 궁금해서 새로운 모델이나 기술이 나오면
직접 찾아보고 공부하는 편이에요."

→ domains: ["AI", "기술"]
→ activities: ["AI 기술 탐색", "관련 내용 학습"]
→ mapped_traits:
   - trait: "탐구성"
   - direction: "strength"

이 경우에는 단순한 관심 표현을 넘어
'직접 찾아보고 공부한다'는 행동 근거가 있기 때문에
탐구성을 추출할 수 있습니다.
"""