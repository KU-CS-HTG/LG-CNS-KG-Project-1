# schemas.py

from pydantic import BaseModel, Field
from typing import Literal


class MappedTrait(BaseModel):
    trait: str = Field(
        description="STANDARD_TRAITS 중 하나"
    )

    direction: Literal[
        "strength",
        "weakness",     # 라벨로만 남긴다 — 약점 영역은 묻지 않고(profile_config), 이 라벨은 어디서도 쓰지 않는다.
                        # 선택지를 둘로 줄이면 경계 성향이 neutral 로 몰려 강점 추출이 흔들린다 (9/16 실측, docs/20260916_인터뷰_평가_회귀_분석.md)
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

    mapped_traits: list[MappedTrait] = Field(default_factory=list)


class StudentProfileAnalysis(BaseModel):
    interest: InterestResult

    study_style: AreaResult

    strength: AreaResult

    life_pattern: AreaResult

    social_style: AreaResult

    values: AreaResult
