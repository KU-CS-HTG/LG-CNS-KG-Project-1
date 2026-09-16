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

    mapped_traits: list[MappedTrait] = Field(default_factory=list)


class StudentProfileAnalysis(BaseModel):
    interest: InterestResult

    study_style: AreaResult

    strength: AreaResult

    weakness: AreaResult

    life_pattern: AreaResult

    social_style: AreaResult

    values: AreaResult
