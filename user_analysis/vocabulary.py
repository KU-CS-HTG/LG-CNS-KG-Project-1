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

8. 각 특성의 방향을 구분합니다.

   strength:
   해당 특성이 학생의 강점으로 명확하게 나타남

   neutral:
   학생의 일반적인 성향 또는 선호로 나타남

9. 서로 상충되는 정보가 있다면
   한쪽 정보를 임의로 제거하지 않습니다.
   대신 confidence를 낮춥니다.

10. 하나의 답변에서 과도하게 많은 성향을 추론하지 않습니다.

11. 친구 수와 협력성을 동일하게 판단하지 않습니다.

12. 생활이 불규칙하다는 이유만으로
    변화적응이 높다고 판단하지 않습니다.

13. 내향적이라는 이유만으로
    발표력, 설득력, 협력성이 낮다고 판단하지 않습니다.

"""
