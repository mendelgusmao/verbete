#!/usr/local/python310/bin/python3.10
from __future__ import annotations
from datetime import datetime
import logging
from pathlib import Path
import random
import os
import sys
import unidecode
from typing import Any, List, Literal, Optional, Tuple
import asyncio, telnetlib3
import string
import secrets
from dataclasses import dataclass
import json

ALPHABET = string.ascii_letters + string.digits


logger = logging.getLogger(__name__)
HERE = Path(__file__).parent.resolve()

RESET = "\u001b[0m"
WHITE = "\u001b[37m"
BLACK = "\u001b[30m"
GREEN = "\u001b[42m\u001b[30m"
YELLOW = "\u001b[43m\u001b[30m"
RED = "\u001b[41m"
CORRECT_PATTERN = [GREEN, GREEN, GREEN, GREEN, GREEN]
Color = Literal[GREEN, YELLOW, RED]

INSTRUCTIONS = f"""VERBETE!\r
\r
Descubra a palavra certa em 6 tentativas.\r
Depois de cada tentativa, as peças mostram o quão perto você está da solução.\r

{GREEN} A {RESET}: A letra faz parte da palavra e estã na posição certa\r
{YELLOW} B {RESET}: A letra faz parte da palavra, mas estã na posição errada\r
{RED} C {RESET}: A letra não faz parte da palavra\r

Digite a senha seguida de ENTER ou somente ENTER para começar uma nova sessão.\r
"""

class InvalidWord(Exception):
    ...

class SessionNotFound(Exception):
    ...


@dataclass
class GameResult:
    won: bool
    tries: int

class Session:
    password: str
    games: List[Game]

    def __init__(self, password: str, games: Optional[List[int]] = None) -> None:
        self.password = password
        self.games = [] if games is None else games

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

CORPUS = os.environ.get("CORPUS") or "corpus.txt"

with open((HERE / f"var/{CORPUS}"), "r") as f:
    WORDS = {
        unidecode.unidecode(w.strip().upper())
        for w in f.readlines()
    }


def generate_password() -> str:
    pw = ''.join(secrets.choice(ALPHABET) for i in range(8)).upper()
    return pw[:4] + "-" + pw[4:]

def load_corpus(seed: int) -> str:
    random.seed(seed+1)
    words = list(WORDS)
    correct = random.choice(words).strip("\n")
    return correct


def check(guess: str, correct: str) -> Tuple[str, int]:
    guess = unidecode.unidecode(guess.upper())

    if guess not in WORDS:
        raise InvalidWord()

    hits = 0
    result = []

    for i, token in enumerate(guess):
        if token == correct[i]:
            color = GREEN
            hits += 1
        elif token in correct:
            color = YELLOW
        else:
            color = RED

        result.append(f"{color} {token} {RESET}")

    return "".join(result), hits

async def get_or_create_session(reader, writer) -> Session:
    buffer = "  "

    while True:
        char = await reader.read(1)
        writer.write(char)

        if char == "\r":
            if len(buffer) == 9:
                try:
                    return Session.get(buffer)
                except SessionNotFound:
                    writer.write("Senha inválida!\r\n")
                    password = generate_password()
                    return Session(password)
            else:
                password = generate_password()
                return Session(password)
        else:
            buffer += char
            continue


async def game(reader, writer):
    writer.write(INSTRUCTIONS)
    session = await get_or_create_session(reader, writer)
    writer.write(f"Senha: {session.password}\r\n")

    seed = datetime.today().toordinal()
    correct = load_corpus(seed)
    print(correct)

    buffer = ""
    progress = []
    tries = 1

    while True:
        char = await reader.read(1)

        if char == "\r":
            writer.write(char)
            guess = buffer
            buffer = ""
        else:
            buffer += char
            writer.write(f"{WHITE} {char.upper()} {RESET}")
            continue

        if len(guess) != 5:
            writer.write("Digite uma palavra com 5 letras!\r\n")
            await writer.drain()
            continue

        result = None
        hits = 0

        try:
            result, hits = check(guess, correct)
        except InvalidWord:
            writer.write("Palavra inválida!\r\n")
            await writer.drain()

        if result:
            progress.append("".join(result))

        if hits == 5:
            writer.write(f"\nSucesso! Acertou em {tries} de 6!\r\n")
            writer.write("\r\n".join(progress))
            await writer.drain()
            writer.close()

            session.add_game(won=True, tries=tries)
        elif tries > 5:
            writer.write("\n\nPerdeu... Boa sorte da próxima!\r\n")
            writer.write("\r\n".join(progress))
            await writer.drain()
            writer.close()

            session.add_game(won=False, tries=tries)
        else:
            for p in progress:
                writer.write(f"{p}\r\n")
            await writer.drain()
            tries += 1


def main():
    loop = asyncio.get_event_loop()
    coro = telnetlib3.create_server(port=6023, shell=game)
    server = loop.run_until_complete(coro)
    loop.run_until_complete(server.wait_closed())


if __name__ == "__main__":
    if os.environ.get("DEBUG"):
        logging.basicConfig(level=logging.DEBUG)

    main()
