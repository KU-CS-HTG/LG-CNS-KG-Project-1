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