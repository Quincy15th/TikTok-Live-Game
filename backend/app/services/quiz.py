"""In-memory quiz engine for the local demonstration mode.

This service deliberately does not connect to TikTok. All answer submissions are
simulated; never expose the demo write endpoints on an untrusted network.
"""
import asyncio
import time
import unicodedata
from collections import defaultdict
from typing import Any

from app.websocket.manager import manager

QUESTIONS = [
    {"prompt": "Áo khoác ngắn", "answer": "jacket"},
    {"prompt": "Quả táo", "answer": "apple"},
    {"prompt": "Con voi", "answer": "elephant"},
    {"prompt": "Bầu trời", "answer": "sky"},
    {"prompt": "Cây cầu", "answer": "bridge"},
    {"prompt": "Ngôi nhà", "answer": "house"},
    {"prompt": "Đại dương", "answer": "ocean"},
    {"prompt": "Con bướm", "answer": "butterfly"},
]


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(text.split())


class QuizGame:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.question_index = 0
        self.question_number = 1
        self.duration = 30
        self.started_at = time.monotonic()
        self.players: dict[str, dict[str, Any]] = {}
        self.correct_this_round: set[str] = set()
        self.recent: list[dict[str, Any]] = []

    def snapshot(self) -> dict[str, Any]:
        question = QUESTIONS[self.question_index]
        remaining = max(0, self.duration - int(time.monotonic() - self.started_at))
        leaderboard = sorted(
            self.players.values(),
            key=lambda player: (-player["score"], -player["correct"], player["name"].casefold()),
        )[:10]
        return {
            "question_number": self.question_number,
            "prompt": question["prompt"],
            "length": len(question["answer"]),
            "hint": question["answer"][:2].upper(),
            "remaining": remaining,
            "duration": self.duration,
            "leaderboard": leaderboard,
            "recent": self.recent[-6:][::-1],
            "mode": "demo",
        }

    def _advance(self) -> None:
        self.question_index = (self.question_index + 1) % len(QUESTIONS)
        self.question_number += 1
        self.started_at = time.monotonic()
        self.correct_this_round.clear()
        self.recent.clear()

    async def get_state(self) -> dict[str, Any]:
        async with self.lock:
            return self.snapshot()

    async def next_question(self) -> dict[str, Any]:
        async with self.lock:
            self._advance()
            state = self.snapshot()
        await manager.broadcast({"type": "game_state", "data": state})
        return state

    async def submit(self, name: str, answer: str) -> dict[str, Any]:
        key = normalize(name)
        async with self.lock:
            if self.snapshot()["remaining"] == 0:
                return {"accepted": False, "reason": "time_up"}
            if normalize(answer) != normalize(QUESTIONS[self.question_index]["answer"]):
                return {"accepted": False, "reason": "incorrect"}
            if key in self.correct_this_round:
                return {"accepted": False, "reason": "already_correct"}
            self.correct_this_round.add(key)
            player = self.players.setdefault(key, {"name": name.strip(), "score": 0, "correct": 0})
            player["score"] += 10
            player["correct"] += 1
            self.recent.append({"name": player["name"], "points": 10})
            state = self.snapshot()
        await manager.broadcast({"type": "game_state", "data": state})
        return {"accepted": True, "points": 10}

    async def run_clock(self) -> None:
        while True:
            await asyncio.sleep(1)
            async with self.lock:
                if self.snapshot()["remaining"] == 0:
                    self._advance()
                state = self.snapshot()
            await manager.broadcast({"type": "game_state", "data": state})


game = QuizGame()
