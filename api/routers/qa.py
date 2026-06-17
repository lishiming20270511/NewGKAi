import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..deps import get_current_streamer

router = APIRouter(prefix="/api/qa", tags=["qa"])

_SYSTEM_PROMPT = (
    "你是一名高考志愿规划顾问，说话风格犀利接地气，类似张雪峰老师。"
    "用口语化语言回答，有数据支撑，200字以内，直接给出结论和建议。"
    '不要废话，不要"首先其次最后"，直接说干货。'
)

_FALLBACK_ANSWER = "AI暂时无法回答，请稍后重试，或者直接问我具体的学校和专业。"


async def _call_llm(question: str) -> str:
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "max_tokens": 400,
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{settings.llm_base_url}/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


@router.post("/ask")
async def ask(
    body: AskRequest,
    current_streamer: dict = Depends(get_current_streamer),
    db: AsyncSession = Depends(get_db),
):
    try:
        answer = await _call_llm(body.question)
    except Exception:
        answer = _FALLBACK_ANSWER

    # Best-effort log to qa_history (non-blocking)
    try:
        await db.execute(
            text("""
                INSERT IGNORE INTO qa_history
                    (streamer_id, question, answer)
                VALUES
                    (:sid, :q, :a)
            """),
            {"sid": current_streamer["id"], "q": body.question[:500], "a": answer[:2000]},
        )
        await db.commit()
    except Exception:
        pass

    return {"answer": answer}
