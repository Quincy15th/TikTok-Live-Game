"""Focused unit and API tests for the quiz engine; no external TikTok connection."""
import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.quiz import QUESTIONS, QuizGame, normalize


def test_normalize_case_and_whitespace() -> None:
    assert normalize("  JACKet  ") == "jacket"


def test_correct_answer_scores_once_and_next_question_resets() -> None:
    async def scenario() -> None:
        game = QuizGame()
        with patch("app.services.quiz.manager.broadcast", new_callable=AsyncMock):
            first = await game.submit("viewer1", "JACKET")
            duplicate = await game.submit("viewer1", "jacket")
            wrong = await game.submit("viewer2", "banana")
            blank_name = await game.submit("   ", "jacket")
            assert first == {"accepted": True, "points": 10}
            assert duplicate["reason"] == "already_correct"
            assert wrong["reason"] == "incorrect"
            assert blank_name["reason"] == "invalid_name"
            assert (await game.get_state())["leaderboard"][0]["score"] == 10
            await game.next_question()
            assert (await game.get_state())["prompt"] == "Quả táo"
            assert (await game.submit("viewer1", "apple"))["accepted"] is True
            assert (await game.get_state())["leaderboard"][0]["score"] == 20

    asyncio.run(scenario())


def test_time_up_rejects_submission_and_questions_wrap_around() -> None:
    async def scenario() -> None:
        game = QuizGame()
        with patch("app.services.quiz.manager.broadcast", new_callable=AsyncMock):
            game.started_at -= game.duration + 1
            expired = await game.submit("viewer1", "jacket")
            assert expired == {"accepted": False, "reason": "time_up"}

            for _ in range(len(QUESTIONS)):
                await game.next_question()
            state = await game.get_state()
            assert state["prompt"] == QUESTIONS[0]["prompt"]
            assert state["question_number"] == len(QUESTIONS) + 1

    asyncio.run(scenario())


def test_game_api_and_websocket_integration() -> None:
    with TestClient(app) as client, client.websocket_connect("/ws") as ws:
        assert ws.receive_json() == {"type": "connected"}

        # Malformed frames return an error payload without dropping the connection.
        ws.send_text("not-json")
        assert ws.receive_json() == {"type": "error", "reason": "invalid_json"}

        # Whitespace-only name or answer is rejected at validation time.
        bad = client.post("/api/game/answer", json={"name": "   ", "answer": "   "})
        assert bad.status_code == 422

        # Advance to a fresh question and verify WebSocket broadcast + answer flow.
        next_resp = client.post("/api/game/next")
        assert next_resp.status_code == 200
        state = next_resp.json()
        ws_msg = ws.receive_json()
        assert ws_msg["type"] == "game_state"
        assert ws_msg["data"]["question_number"] == state["question_number"]

        answer_map = {q["prompt"]: q["answer"] for q in QUESTIONS}
        correct = answer_map[state["prompt"]]
        ok_resp = client.post(
            "/api/game/answer",
            json={"name": "tester", "answer": correct.upper()},
        )
        assert ok_resp.json() == {"accepted": True, "points": 10}
        scored_msg = ws.receive_json()
        assert scored_msg["type"] == "game_state"
        assert any(
            p["name"] == "tester" and p["score"] >= 10
            for p in scored_msg["data"]["leaderboard"]
        )
