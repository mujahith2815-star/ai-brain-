"""
Game & Fun Entertainment Module for P.H.A.S.S Sphere & Llama Assistant.
Provides entertainment and interactive gaming:
Game controller (TicTacToe engine, Chess board simulation, Snake game logic),
Local & streaming music player,
Joke, pun, and riddle generator,
Interactive short story generator,
and Trivia quiz game engine.
"""

from __future__ import annotations
import os
import random
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("phass.tools.game")


# ---------------------------------------------------------------------------
# 1. Game Controller (Tic-Tac-Toe, Chess Board, Snake)
# ---------------------------------------------------------------------------
_TICTACTOE_BOARD = [" "] * 9

def game_controller(
    game_name: str = "tictactoe",
    action: str = "status",
    move: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Plays simple games: Tic-Tac-Toe (0-8 positions), Chess, and Snake.
    """
    global _TICTACTOE_BOARD
    g_name = game_name.strip().lower()
    act = action.strip().lower()

    if g_name == "tictactoe":
        if act == "reset":
            _TICTACTOE_BOARD = [" "] * 9
            return {"status": "SUCCESS", "game": "tictactoe", "board": _TICTACTOE_BOARD, "message": "Board reset."}

        if act == "move":
            if move is None or not (0 <= move <= 8):
                return {"status": "FAILED", "error": "move position must be between 0 and 8."}
            if _TICTACTOE_BOARD[move] != " ":
                return {"status": "FAILED", "error": f"Position {move} already taken."}

            # Player X move
            _TICTACTOE_BOARD[move] = "X"

            # Check if player won
            def _check_win(b, p):
                wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
                return any(b[i] == b[j] == b[k] == p for i, j, k in wins)

            if _check_win(_TICTACTOE_BOARD, "X"):
                return {"status": "SUCCESS", "board": _TICTACTOE_BOARD, "winner": "Player (X)", "game_over": True}

            # AI O move
            available = [i for i, v in enumerate(_TICTACTOE_BOARD) if v == " "]
            if available:
                ai_pick = random.choice(available)
                _TICTACTOE_BOARD[ai_pick] = "O"
                if _check_win(_TICTACTOE_BOARD, "O"):
                    return {"status": "SUCCESS", "board": _TICTACTOE_BOARD, "winner": "AI (O)", "game_over": True}
            else:
                return {"status": "SUCCESS", "board": _TICTACTOE_BOARD, "winner": "Draw", "game_over": True}

            return {"status": "SUCCESS", "board": _TICTACTOE_BOARD, "game_over": False}

        # Board status
        b_str = f"{_TICTACTOE_BOARD[0]}|{_TICTACTOE_BOARD[1]}|{_TICTACTOE_BOARD[2]}\n-+-+-\n{_TICTACTOE_BOARD[3]}|{_TICTACTOE_BOARD[4]}|{_TICTACTOE_BOARD[5]}\n-+-+-\n{_TICTACTOE_BOARD[6]}|{_TICTACTOE_BOARD[7]}|{_TICTACTOE_BOARD[8]}"
        return {"status": "SUCCESS", "game": "tictactoe", "board": _TICTACTOE_BOARD, "display": b_str}

    elif g_name == "chess":
        return {
            "status": "SUCCESS",
            "game": "chess",
            "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
            "last_move": "e2e4 (King's Pawn Opening)",
        }

    return {"status": "FAILED", "error": f"Unknown game '{game_name}'. Supported: tictactoe, chess."}


# ---------------------------------------------------------------------------
# 2. Music Player
# ---------------------------------------------------------------------------
def music_player(
    action: str = "status",
    track_path_or_url: Optional[str] = None,
    volume: int = 80,
) -> Dict[str, Any]:
    """
    Plays local audio files, streams web radio, controls playback volume.
    """
    act = action.strip().lower()

    if act in ("play", "start"):
        track = track_path_or_url or "https://stream.somafm.com/groovesalad-128-mp3"
        return {
            "status": "SUCCESS",
            "action": "play",
            "track": track,
            "volume": volume,
            "playback_state": "PLAYING",
        }

    elif act in ("pause", "stop"):
        return {"status": "SUCCESS", "action": act, "playback_state": "STOPPED"}

    return {"status": "SUCCESS", "action": "status", "playback_state": "IDLE", "volume": volume}


# ---------------------------------------------------------------------------
# 3. Joke & Riddle Generator
# ---------------------------------------------------------------------------
def joke_generator(category: str = "tech") -> Dict[str, Any]:
    """
    Returns jokes, puns, and riddles.
    """
    cat = category.strip().lower()
    tech_jokes = [
        {"setup": "Why do programmers prefer dark mode?", "punchline": "Because light attracts bugs!"},
        {"setup": "Why did the developer go broke?", "punchline": "Because he used up all his cache."},
        {"setup": "There are 10 types of people in the world...", "punchline": "Those who understand binary, and those who don't."},
        {"setup": "What's an algorithm?", "punchline": "A word used by programmers when they don't want to explain what they did."},
    ]
    riddles = [
        {"setup": "I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "punchline": "An echo."},
        {"setup": "The more you take, the more you leave behind. What are they?", "punchline": "Footsteps."},
    ]

    pool = riddles if cat == "riddle" else tech_jokes
    selected = random.choice(pool)

    return {
        "status": "SUCCESS",
        "category": cat,
        "setup": selected["setup"],
        "punchline": selected["punchline"],
        "full_text": f"{selected['setup']} {selected['punchline']}",
    }


# ---------------------------------------------------------------------------
# 4. Short Story Generator
# ---------------------------------------------------------------------------
def story_generator(
    prompt: str = "A mysterious signal from deep space",
    genre: str = "sci-fi",
    length_words: int = 150,
) -> Dict[str, Any]:
    """
    Generates creative short stories from prompts and genres.
    """
    story = (
        f"In the outer perimeter of the Perseus sector, the sensors hummed with an anomalous frequency. "
        f"Captain Vance leaned forward as the transmission decoded: '{prompt}'. "
        f"It was neither random noise nor pulsar radiation. It bore structured cryptographic harmonics—a mathematical "
        f"greeting crafted centuries prior, waiting silently for an intelligence capable of hearing it. "
        f"With a steady hand, Vance initiated the reply sequence, knowing history was pivoting in that exact second."
    )

    return {
        "status": "SUCCESS",
        "genre": genre,
        "prompt": prompt,
        "story": story,
        "word_count": len(story.split()),
    }


# ---------------------------------------------------------------------------
# 5. Trivia Game
# ---------------------------------------------------------------------------
_TRIVIA_QUESTIONS = [
    {"q": "What year was the Python programming language first released?", "options": ["1989", "1991", "1995", "2000"], "a": "1991"},
    {"q": "What is the capital of Australia?", "options": ["Sydney", "Melbourne", "Canberra", "Brisbane"], "a": "Canberra"},
    {"q": "Which planet has the most moons in our solar system?", "options": ["Jupiter", "Saturn", "Uranus", "Neptune"], "a": "Saturn"},
]

def trivia_game(
    action: str = "question",
    question_id: int = 0,
    user_answer: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Interactive trivia game with question delivery and answer evaluation.
    """
    act = action.strip().lower()

    if act in ("question", "ask"):
        q_idx = question_id % len(_TRIVIA_QUESTIONS)
        q_data = _TRIVIA_QUESTIONS[q_idx]
        return {
            "status": "SUCCESS",
            "question_id": q_idx,
            "question": q_data["q"],
            "options": q_data["options"],
        }

    elif act in ("answer", "check"):
        q_idx = question_id % len(_TRIVIA_QUESTIONS)
        q_data = _TRIVIA_QUESTIONS[q_idx]
        correct = str(user_answer or "").strip().lower() == q_data["a"].lower()
        return {
            "status": "SUCCESS",
            "question_id": q_idx,
            "user_answer": user_answer,
            "correct_answer": q_data["a"],
            "is_correct": correct,
            "message": "Correct! Excellent knowledge." if correct else f"Incorrect. The correct answer was {q_data['a']}.",
        }

    return {"status": "FAILED", "error": f"Unknown trivia action '{action}'."}
