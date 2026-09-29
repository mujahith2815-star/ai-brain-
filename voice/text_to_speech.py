"""
Text-to-Speech (TTS) module for Orvix Sphere using pyttsx3 (SAPI5 offline).
Provides non-blocking, interruptible speech synthesis with thread safety.
"""

import os
import time
import queue
import logging
import threading
from typing import Optional, List, Dict, Any

from config.voice_config import voice_config

logger = logging.getLogger("orvix.voice.tts")


class SpeechSynthesizer:
    """
    Thread-safe, non-blocking text-to-speech synthesizer using pyttsx3 (SAPI5).
    """

    def __init__(
        self,
        rate: Optional[int] = None,
        volume: Optional[float] = None,
        voice_id: Optional[str] = None
    ):
        self.rate = rate if rate is not None else voice_config.tts_rate
        self.volume = volume if volume is not None else voice_config.tts_volume
        self.voice_id = voice_id or voice_config.tts_voice_id
        self._queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._is_busy = False
        self._worker_thread: Optional[threading.Thread] = None
        self._engine = None
        self._initialized = False
        self._init_worker()

    def _init_worker(self):
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="TTS-Worker")
        self._worker_thread.start()

    def _worker_loop(self):
        # Initialize pyttsx3 inside the worker thread for Windows SAPI5 COM apartment stability
        try:
            import pyttsx3
            if os.name == "nt":
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                except Exception:
                    pass
            self._engine = pyttsx3.init()
            if self._engine:
                self._engine.setProperty("rate", self.rate)
                self._engine.setProperty("volume", self.volume)
                if self.voice_id:
                    self._engine.setProperty("voice", self.voice_id)
                self._initialized = True
        except Exception as e:
            logger.warning(f"pyttsx3 initialization notice: {e}")
            self._engine = None
            self._initialized = False

        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if item is None or self._stop_event.is_set():
                self._queue.task_done()
                break

            text, done_event = item
            self._is_busy = True
            try:
                if self._engine:
                    self._engine.say(text)
                    self._engine.runAndWait()
            except Exception as e:
                logger.debug(f"TTS playback exception: {e}")
            finally:
                self._is_busy = False
                if done_event:
                    done_event.set()
                self._queue.task_done()

    def speak(self, text: str, block: bool = False) -> bool:
        """
        Synthesize text into speech. Non-blocking by default.
        If block=True, waits until synthesis completes.
        """
        if not text or not str(text).strip():
            return False

        if not self._worker_thread or not self._worker_thread.is_alive():
            self._init_worker()

        clean_text = str(text).strip()
        done_event = threading.Event() if block else None
        self._queue.put((clean_text, done_event))

        if block and done_event:
            done_event.wait()
        return True

    def stop(self) -> None:
        """Interrupts speech immediately and empties the pending queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Exception:
                break

        if self._engine:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._is_busy = False

    def set_rate(self, rate: int) -> None:
        self.rate = int(rate)
        if self._engine:
            try:
                self._engine.setProperty("rate", self.rate)
            except Exception:
                pass

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, float(volume)))
        if self._engine:
            try:
                self._engine.setProperty("volume", self.volume)
            except Exception:
                pass

    def set_voice(self, voice_id: str) -> bool:
        self.voice_id = voice_id
        if self._engine:
            try:
                self._engine.setProperty("voice", voice_id)
                return True
            except Exception:
                return False
        return False

    def list_voices(self) -> List[Dict[str, Any]]:
        voices_list = []
        if self._engine:
            try:
                voices = self._engine.getProperty("voices")
                for v in voices:
                    voices_list.append({
                        "id": getattr(v, "id", ""),
                        "name": getattr(v, "name", ""),
                        "languages": getattr(v, "languages", []),
                        "gender": getattr(v, "gender", ""),
                    })
            except Exception:
                pass
        return voices_list

    @property
    def is_busy(self) -> bool:
        return self._is_busy

    def close(self):
        self._stop_event.set()
        self._queue.put(None)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
