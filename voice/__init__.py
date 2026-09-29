"""
Voice Interface Package for Orvix Sphere / P.H.A.S.S.
Provides 100% offline, local wake word detection, Whisper STT, pyttsx3 TTS, and VoiceLoop.
"""

from voice.text_to_speech import SpeechSynthesizer
from voice.speech_to_text import SpeechRecognizer
from voice.wake_word import WakeWordDetector
from voice.voice_loop import VoiceLoop

__all__ = [
    "SpeechSynthesizer",
    "SpeechRecognizer",
    "WakeWordDetector",
    "VoiceLoop",
]
