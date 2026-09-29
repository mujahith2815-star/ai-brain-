"""
Native J.A.R.V.I.S. Voice & Speech Synthesis Engine for P.H.A.S.S Sphere.
Provides real-time non-blocking verbal audio output using native Windows Speech SAPI / PowerShell / pyttsx3.
"""

from __future__ import annotations
import os
import subprocess
import sys
import threading
import queue
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("phass.voice.speech_engine")


@dataclass
class SpeechEvent:
    text: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_est_sec: float = 1.0
    was_spoken: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "timestamp": self.timestamp,
            "duration_est_sec": round(self.duration_est_sec, 2),
            "was_spoken": self.was_spoken,
        }


class JARVISVoiceEngine:
    def __init__(self):
        self.is_muted = False
        self.speech_queue: queue.Queue = queue.Queue()
        self.speech_history: List[SpeechEvent] = []
        self.is_speaking = False
        self.rate = 1.0  # Speed multiplier
        self.volume = 100 # 0 to 100

        # Start background audio playback worker thread
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    def speak(self, text: str, non_blocking: bool = True) -> SpeechEvent:
        """
        Synthesizes and speaks text using native OS voice audio.
        """
        clean_text = text.strip()
        if not clean_text:
            return SpeechEvent("", was_spoken=False)

        # Estimate duration (~3 words per second)
        word_count = len(clean_text.split())
        est_sec = max(0.8, word_count / 3.2)
        event = SpeechEvent(text=clean_text, duration_est_sec=est_sec, was_spoken=not self.is_muted)
        self.speech_history.append(event)

        if not self.is_muted:
            if non_blocking:
                self.speech_queue.put(clean_text)
            else:
                self._synthesize_audio_direct(clean_text)

        return event

    def _speech_worker(self) -> None:
        while True:
            try:
                phrase = self.speech_queue.get()
                if phrase is None:
                    break
                self.is_speaking = True
                self._synthesize_audio_direct(phrase)
                self.is_speaking = False
                self.speech_queue.task_done()
            except Exception as e:
                logger.error(f"Speech synthesis error: {e}")
                self.is_speaking = False

    def _synthesize_audio_direct(self, text: str) -> None:
        """
        Invokes native Windows SAPI TTS voice via PowerShell or Python SAPI.
        """
        if sys.platform == "win32":
            # Sanitize single and double quotes for PowerShell SAPI
            escaped = text.replace("'", " ").replace('"', ' ').replace("\n", " ")
            # Use Windows System.Speech.Synthesis.SpeechSynthesizer
            ps_cmd = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$synth.Rate = 1; $synth.Volume = {self.volume}; "
                f"$synth.Speak('{escaped[:250]}')"
            )
            try:
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True,
                    timeout=8,
                )
            except Exception:
                pass
        else:
            # Fallback on POSIX
            try:
                subprocess.run(["say", text], capture_output=True, timeout=5)
            except Exception:
                pass

    def set_rate(self, rate_wpm: int) -> None:
        sapi_rate = max(-5, min(5, int((rate_wpm - 175) / 15)))
        self.rate = sapi_rate

    def set_volume(self, volume: float) -> None:
        self.volume = max(0, min(100, int(volume * 100 if volume <= 1.0 else volume)))

    def toggle_mute(self, muted: Optional[bool] = None) -> bool:
        if muted is None:
            self.is_muted = not self.is_muted
        else:
            self.is_muted = muted
        return self.is_muted

    def get_speech_telemetry(self) -> Dict[str, Any]:
        return {
            "is_muted": self.is_muted,
            "is_speaking": self.is_speaking,
            "total_phrases_spoken": len(self.speech_history),
            "queue_depth": self.speech_queue.qsize(),
            "last_phrase": self.speech_history[-1].text if self.speech_history else None,
        }


voice_engine = JARVISVoiceEngine()
