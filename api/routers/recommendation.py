from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..deps import get_current_streamer
from ..services.recommendation import RecommendRequest as SvcReq, generate_recommendation

router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])

# Province max scores
_SCORE_MAX: dict[str, int] = {"上海": 660}
_DEFAULT_SCORE_MAX = 750


class GenerateRequest(BaseModel):
    province: str = Field(..., min_length=2, max_length=32)
    score: int = Field(..., ge=0, le=900)
    subject_category: str = Field(..., min_length=2, max_length=16)
    rank: Optional[int] = Field(None, ge=1)
    city_preference: list[str] = Field(default_factory=list)
    intended_schools: list[str] = Field(default_factory=list, max_length=3)
    major_preference: list[str] = Field(default_factory=list)
    personality: list[str] = Field(default_factory=list)
    economic_level: str = Field("一般", max_length=16)

    @field_validator("score")
    @classmethod
    def validate_score(cls, v, info):
        province = info.data.get("province", "")
        max_score = _SCORE_MAX.get(province, _DEFAULT_SCORE_MAX)
        if v > max_score:
            raise ValueError(f"分数超出该省满分 {max_score}")
        return v


@router.post("/generate")
async def generate(
    body: GenerateRequest,
    current_streamer: dict = Depends(get_current_streamer),
    db: AsyncSession = Depends(get_db),
):
    max_score = _SCORE_MAX.get(body.province, _DEFAULT_SCORE_MAX)
    if body.score > max_score:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"分数超出该省满分",
        )

    req = SvcReq(
        province=body.province,
        score=body.score,
        subject_category=body.subject_category,
        rank=body.rank,
        city_preference=body.city_preference,
        intended_schools=body.intended_schools,
        major_preference=body.major_preference,
        personality=body.personality,
        economic_level=body.economic_level,
    )

    result = await generate_recommendation(req, db)
    return result
