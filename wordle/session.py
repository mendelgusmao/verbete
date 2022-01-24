from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import secrets
import string
from typing import Any, Dict, List, Optional

HERE = Path(__file__).parent.parent.resolve()
ALPHABET = string.ascii_letters + string.digits


def generate_password() -> str:
    pw = ''.join(secrets.choice(ALPHABET) for i in range(8)).upper()
    return pw[:4] + "-" + pw[4:]


class SessionNotFound(Exception):
    ...


@dataclass
class GameResult:
    won: bool
    tries: int


@dataclass
class Session:
    password: Optional[str] = generate_password()
    games: Optional[List[GameResult]] = None

    def add_game(self, won: bool, tries: int) -> None:
        game = GameResult(won=won, tries=tries)
        self.games.append(game.__dict__)

        session_file = HERE / "sessions" / self.password

        with open(session_file, 'w') as f:
            json.dump(self.games, f)

    def stats(self) -> Dict[str, Any]:
        games = len(self.games)
        wins = len([g for g in self.games if g.won])
        distribution = defaultdict(int)

        for game in games:
            distribution[game.tries] += 1

        return {
            "games": games,
            "wins": wins,
            "current_streak": 0,
            "max_streak": 0,
            "distribution": distribution,
        }

    @staticmethod
    def get(password: str) -> Session:
        try:
            session_file = HERE / "sessions" / password

            with open(session_file, "r") as f:
                games = json.load(f)
                return Session(password, games)
        except FileNotFound:
            raise SessionNotFound()
