import pytest
import os
from tools.fun_tools import (
    image_generator,
    story_generator,
    joke_generator,
    trivia_game,
    music_player,
    game_controller,
)


def test_image_generator():
    res = image_generator("Futuristic Quantum Computer in Space", "memory_vault/quantum.svg")
    assert res["status"] == "SUCCESS"
    assert os.path.exists("memory_vault/quantum.svg")
    assert "SVG" in res["format"]


def test_story_generator():
    res = story_generator(genre="cyberpunk", prompt="A rogue AI infiltrating the mainframe")
    assert res["status"] == "SUCCESS"
    assert "story" in res
    assert len(res["story"]) > 50


def test_joke_generator():
    res = joke_generator(category="programming")
    assert res["status"] == "SUCCESS"
    assert "joke" in res
    assert len(res["joke"]) > 5


def test_trivia_game():
    q = trivia_game(action="question")
    assert q["status"] == "SUCCESS"
    assert "question" in q
    assert len(q["options"]) == 4

    ans = trivia_game(action="answer", answer="Central Processing Unit")
    assert ans["status"] == "SUCCESS"
    assert ans["correct"] is True


def test_music_player():
    play = music_player("play", track="lofi_chill_beats_01")
    assert play["status"] == "SUCCESS"
    assert play["state"] == "playing"

    pause = music_player("pause")
    assert pause["status"] == "SUCCESS"
    assert pause["state"] == "paused"


def test_game_controller():
    res = game_controller("tictactoe", "status")
    assert res["status"] == "SUCCESS"
    assert res["game"] == "TicTacToe"
    assert len(res["board"]) == 3