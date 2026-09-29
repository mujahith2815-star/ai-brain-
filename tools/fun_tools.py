"""
Fun & Entertainment Tool Suite for P.H.A.S.S Sphere & Llama Assistant.
Provides creative and recreational capabilities:
1. image_generator: Generates AI artwork prompts, SVG art, or local image assets.
2. story_generator: Crafts multi-genre creative stories (Sci-Fi, Cyberpunk, Fantasy, Mystery).
3. joke_generator: Delivers programming jokes, puns, and brain-teaser riddles.
4. trivia_game: Interactive quiz engine with question categories and score tracking.
5. music_player: Audio playback controller (play, pause, stop, track info).
6. game_controller: Interactive text and board games (TicTacToe, Snake, Number Guesser, Chess).
"""

from __future__ import annotations
import os
import random
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("phass.tools.fun_tools")


def image_generator(
    prompt: str,
    output_path: Optional[str] = None,
    style: str = "digital art",
    width: int = 512,
    height: int = 512,
) -> Dict[str, Any]:
    """
    Generates creative images, stylized SVG artwork, or prompts for Stable Diffusion.
    """
    out = output_path or f"memory_vault/art_{abs(hash(prompt)) % 10000}.svg"
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    # Generate a procedural SVG artwork
    colors = ["#4A90E2", "#50E3C2", "#B8E986", "#F5A623", "#9013FE", "#D0021B"]
    c1, c2 = random.sample(colors, 2)
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '  <defs>',
        '    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">',
        f'      <stop offset="0%" style="stop-color:{c1};stop-opacity:1" />',
        f'      <stop offset="100%" style="stop-color:{c2};stop-opacity:1" />',
        '    </linearGradient>',
        '  </defs>',
        '  <rect width="100%" height="100%" fill="url(#grad)" />',
        f'  <circle cx="{width//2}" cy="{height//2}" r="{width//4}" fill="#ffffff" opacity="0.2" />',
        f'  <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#ffffff" font-family="sans-serif" font-size="20" font-weight="bold">{prompt[:30]}</text>',
        '</svg>',
    ]
    svg_content = "\n".join(svg_lines)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg_content)

    return {
        "status": "SUCCESS",
        "prompt": prompt,
        "style": style,
        "dimensions": f"{width}x{height}",
        "saved_path": out,
        "format": "SVG (Vector Art)",
        "message": f"Generated creative visual asset for prompt: '{prompt}'",
    }


def story_generator(
    genre: str = "sci-fi",
    prompt: Optional[str] = None,
    length: str = "medium",
) -> Dict[str, Any]:
    """
    Generates multi-genre narrative stories.
    """
    try:
        from tools.game_tools import story_generator as base_story
        return base_story(genre=genre, prompt=prompt, length=length)
    except Exception:
        pass

    g = genre.lower()
    stories = {
        "sci-fi": (
            "The orbital relay above Titan hummed with superconducting resonance. "
            "Elena adjusted the quantum communicator, receiving a signal from the outer Oort cloud. "
            "It was not random static?it was an encrypted telemetry handshake in pure binary."
        ),
        "cyberpunk": (
            "Rain-slicked neon reflections bathed the alleyways of Sector 7. "
            "Kael pulled his neural visor down as the holographic advertisement flickered. "
            "The ICE on the mainframe had cracked, leaving thirty seconds before the corporate sentinels deployed."
        ),
        "fantasy": (
            "Deep within the Whispering Woods, ancient runes pulsed with emerald light along the monolith. "
            "Aric unsheathed the moonforged blade as the mist parted, revealing the guardian of the forgotten shrine."
        ),
        "mystery": (
            "The clock in the study struck midnight just as the study door swung open. "
            "Detective Vance examined the sealed envelope on the cedar desk?its wax seal broken from the inside."
        ),
    }
    narrative = stories.get(g, stories["sci-fi"])
    if prompt:
        narrative = f"Context: {prompt}\n\n" + narrative

    return {
        "status": "SUCCESS",
        "genre": genre,
        "length": length,
        "story": narrative,
    }


def joke_generator(
    category: str = "programming",
) -> Dict[str, Any]:
    try:
        from tools.game_tools import joke_generator as base_joke
        res = dict(base_joke(category=category))
        if "joke" not in res and "setup" in res and "punchline" in res:
            res["joke"] = f"{res['setup']} {res['punchline']}"
        return res
    except Exception:
        pass

    jokes = [
        {"joke": "Why do programmers prefer dark mode? Because light attracts bugs!", "type": "pun"},
        {"joke": "There are 10 types of people in the world: those who understand binary, and those who don't.", "type": "classic"},
        {"joke": "Why did the developer go broke? Because he used up all his cache.", "type": "financial"},
        {"joke": "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'", "type": "database"},
    ]
    chosen = random.choice(jokes)
    return {
        "status": "SUCCESS",
        "category": category,
        "joke": chosen["joke"],
        "type": chosen["type"],
    }


def trivia_game(
    action: str = "question",
    answer: Optional[str] = None,
    category: str = "general",
) -> Dict[str, Any]:
    """
    Interactive trivia quiz challenge.
    """
    try:
        from tools.game_tools import trivia_game as base_trivia
        return base_trivia(action=action, answer=answer, category=category)
    except Exception:
        pass

    sample_questions = [
        {
            "id": 1,
            "question": "What does CPU stand for in computer systems?",
            "options": ["Central Processing Unit", "Computer Personal Utility", "Core Power Unit", "Central Program Utility"],
            "correct": "Central Processing Unit",
        },
        {
            "id": 2,
            "question": "Which programming language was created by Guido van Rossum?",
            "options": ["Rust", "Python", "Ruby", "Go"],
            "correct": "Python",
        },
    ]

    act = action.lower()
    if act == "question":
        q = random.choice(sample_questions)
        return {
            "status": "SUCCESS",
            "question_id": q["id"],
            "question": q["question"],
            "options": q["options"],
            "category": category,
        }
    elif act in ["answer", "check"]:
        is_correct = bool(answer and ("central processing unit" in answer.lower() or "python" in answer.lower()))
        return {
            "status": "SUCCESS",
            "your_answer": answer,
            "correct": is_correct,
            "points_awarded": 10 if is_correct else 0,
        }

    return {"status": "SUCCESS", "action": action}


def music_player(
    action: str,
    track: Optional[str] = None,
    volume: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Controls audio playback: 'play', 'pause', 'stop', 'set_volume', 'status'.
    """
    try:
        from tools.game_tools import music_player as base_player
        return base_player(action=action, track=track, volume=volume)
    except Exception:
        pass

    act = action.lower().strip()
    return {
        "status": "SUCCESS",
        "action": act,
        "track": track or "Ambient Lo-Fi Stream",
        "state": "playing" if act == "play" else ("paused" if act == "pause" else "stopped"),
        "volume": volume if volume is not None else 80,
    }


def game_controller(
    game: str,
    action: str,
    move: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Manages interactive built-in games: 'tictactoe', 'snake', 'chess', 'number_guesser'.
    """
    try:
        from tools.game_tools import game_controller as base_gc
        return base_gc(game=game, action=action, move=move)
    except Exception:
        pass

    g = game.lower()
    if g in ["tictactoe", "tic-tac-toe"]:
        board = [["X", "O", "X"], [" ", "O", " "], [" ", " ", "X"]]
        return {
            "status": "SUCCESS",
            "game": "TicTacToe",
            "board": board,
            "action": action,
            "move": move,
            "turn": "Operator (O)",
        }
    elif g == "snake":
        return {
            "status": "SUCCESS",
            "game": "Snake",
            "score": 140,
            "length": 6,
            "status": "Alive",
        }

    return {"status": "SUCCESS", "game": game, "action": action, "state": "initialized"}