"""Focused unit tests for the quiz engine; no external TikTok connection."""
import asyncio
from unittest.mock import AsyncMock, patch

from app.services.quiz import QuizGame, normalize


def test_normalize_case_and_whitespace() -> None:
    assert normalize("  JACKet  ") == "jacket"


def test_correct_answer_scores_once_and_next_question_resets() -> None:
    async def scenario() -> None:
        game = QuizGame()
        with patch("app.services.quiz.manager.broadcast", new_callable=AsyncMock):
            first = await game.submit("viewer1", "JACKET")
            duplicate = await game.submit("viewer1", "jacket")
            wrong = await game.submit("viewer2", "banana")
            assert first == {"accepted": True, "points": 10}
            assert duplicate["reason"] == "already_correct"
            assert wrong["reason"] == "incorrect"
            assert (await game.get_state())["leaderboard"][0]["score"] == 10
            await game.next_question()
            assert (await game.get_state())["prompt"] == "Quả táo"
            assert (await game.submit("viewer1", "apple"))["accepted"] is True
            assert (await game.get_state())["leaderboard"][0]["score"] == 20

    asyncio.run(scenario())
