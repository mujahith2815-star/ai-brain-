"""
Voice Configuration Module for Orvix Sphere / P.H.A.S.S.
Centralizes all voice-related settings: wake word, speech-to-text, text-to-speech, audio devices, and fallbacks.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional


@dataclass
class VoiceConfig:
    # Global enablement
    voice_enabled: bool = True
    fallback_to_text: bool = True
    log_to_knowledge_store: bool = True

    # Wake word detection
    wake_word: str = "hey orvix"
    wake_words: List[str] = field(default_factory=lambda: ["hey orvix", "orvix", "hey llama", "jarvis"])
    porcupine_access_key: str = field(default_factory=lambda: os.getenv("PORCUPINE_ACCESS_KEY", ""))
    porcupine_keyword: str = "jarvis"
    keyboard_fallback_hotkey: str = "ctrl+shift+o"
    wake_word_sensitivity: float = 0.5
    wake_word_timeout: float = 10.0

    # Speech-to-Text (STT) - Whisper
    whisper_model: str = "tiny"  # 'tiny' or 'base' for fast local CPU inference
    whisper_language: str = "en"
    audio_sample_rate: int = 16000
    audio_channels: int = 1
    listen_timeout: float = 5.0
    phrase_time_limit: float = 10.0
    silence_threshold: float = 0.005

    # Text-to-Speech (TTS) - pyttsx3 (SAPI5 on Windows)
    tts_rate: int = 185          # words per minute
    tts_volume: float = 0.9      # 0.0 to 1.0
    tts_voice_id: Optional[str] = None
    tts_engine_name: str = "sapi5" if os.name == "nt" else "dummy"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save_to_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_json(cls, path: Path) -> "VoiceConfig":
        if not path.exists():
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except Exception:
            return cls()


# Default singleton instance
voice_config = VoiceConfig()

# Export uppercase constants for quick direct access
VOICE_ENABLED = voice_config.voice_enabled
WAKE_WORD = voice_config.wake_word
WAKE_WORDS = voice_config.wake_words
WHISPER_MODEL = voice_config.whisper_model
TTS_RATE = voice_config.tts_rate
TTS_VOLUME = voice_config.tts_volume
LISTEN_TIMEOUT = voice_config.listen_timeout
FALLBACK_TO_TEXT = voice_config.fallback_to_text
KEYBOARD_FALLBACK_HOTKEY = voice_config.keyboard_fallback_hotkey
LOG_TO_KNOWLEDGE_STORE = voice_config.log_to_knowledge_store
