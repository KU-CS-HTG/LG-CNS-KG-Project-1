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