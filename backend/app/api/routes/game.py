"""REST endpoints for the explicitly simulated quiz demo."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.quiz import game

router = APIRouter(prefix="/game", tags=["game"])


class AnswerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    answer: str = Field(min_length=1, max_length=100)


@router.get("/state")
async def state() -> dict:
    return await game.get_state()


@router.post("/answer")
async def answer(payload: AnswerRequest) -> dict:
    return await game.submit(payload.name, payload.answer)


@router.post("/next")
async def next_question() -> dict:
    return await game.next_question()
