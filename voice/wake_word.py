"""
Wake Word Detection module for Orvix Sphere.
Supports pvporcupine with automatic keyboard shortcut (Ctrl+Shift+O) fallback.
"""

import time
import struct
import logging
import threading
from typing import Optional

from config.voice_config import VoiceConfig, voice_config

logger = logging.getLogger("orvix.voice.wake_word")


class WakeWordDetector:
    """
    Detects wake word via Porcupine acoustic detection or keyboard hotkey fallback.
    """

    def __init__(
        self,
        keyword: Optional[str] = None,
        access_key: Optional[str] = None,
        hotkey: Optional[str] = None,
        config: Optional[VoiceConfig] = None,
    ):
        self.config = config or voice_config
        self.keyword = keyword or self.config.porcupine_keyword
        self.access_key = access_key or self.config.porcupine_access_key
        self.hotkey = hotkey or self.config.keyboard_fallback_hotkey
        self._stop_event = threading.Event()
        self._triggered_event = threading.Event()
        self._porcupine = None
        self._pa = None
        self._audio_stream = None
        self._hotkey_hooked = False

        self._init_detector()

    def _init_detector(self):
        # Try initializing pvporcupine if access key is provided
        if self.access_key:
            try:
                import pvporcupine
                self._porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=[self.keyword]
                )
                import pyaudio
                self._pa = pyaudio.PyAudio()
                self._audio_stream = self._pa.open(
                    rate=self._porcupine.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=self._porcupine.frame_length
                )
                logger.info(f"Porcupine wake word detector initialized for '{self.keyword}'")
            except Exception as e:
                logger.info(f"Porcupine initialization skipped ({e}); hotkey fallback '{self.hotkey}' enabled.")
                self._cleanup_porcupine()

        # Always register keyboard fallback hotkey
        self._setup_hotkey()

    def _setup_hotkey(self):
        try:
            import keyboard
            def _on_hotkey():
                logger.info(f"Wake hotkey '{self.hotkey}' pressed.")
                self._triggered_event.set()
            keyboard.add_hotkey(self.hotkey, _on_hotkey)
            self._hotkey_hooked = True
        except Exception as e:
            logger.debug(f"Keyboard hotkey hook could not be registered: {e}")
            self._hotkey_hooked = False

    def trigger(self):
        """Programmatically triggers the wake word (useful for tests and CLI simulation)."""
        self._triggered_event.set()

    def wait_for_wake_word(self, timeout: Optional[float] = None) -> bool:
        """
        Blocks until wake word is triggered via audio or keyboard hotkey.
        Returns True if triggered, False if timed out or stopped.
        """
        if self._triggered_event.is_set():
            self._triggered_event.clear()
            return True

        self._stop_event.clear()
        start_time = time.time()

        # If Porcupine audio stream is active, process frames
        if self._audio_stream and self._porcupine:
            try:
                while not self._stop_event.is_set():
                    if self._triggered_event.is_set():
                        self._triggered_event.clear()
                        return True

                    if timeout and (time.time() - start_time) >= timeout:
                        return False

                    pcm = self._audio_stream.read(self._porcupine.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * self._porcupine.frame_length, pcm)
                    result = self._porcupine.process(pcm)
                    if result >= 0:
                        return True
            except Exception as e:
                logger.warning(f"Audio stream error in wake detector: {e}")

        # Hotkey / fallback mode: wait on event with timeout
        poll_interval = 0.1
        while not self._stop_event.is_set():
            if self._triggered_event.wait(timeout=poll_interval):
                self._triggered_event.clear()
                return True
            if timeout and (time.time() - start_time) >= timeout:
                return False

        return False

    def stop(self):
        """Stops listening and unhooks hotkey."""
        self._stop_event.set()
        self._cleanup_porcupine()
        if self._hotkey_hooked:
            try:
                import keyboard
                keyboard.remove_hotkey(self.hotkey)
            except Exception:
                pass
            self._hotkey_hooked = False

    def _cleanup_porcupine(self):
        if self._audio_stream:
            try:
                self._audio_stream.stop_stream()
                self._audio_stream.close()
            except Exception:
                pass
            self._audio_stream = None
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        if self._porcupine:
            try:
                self._porcupine.delete()
            except Exception:
                pass
            self._porcupine = None
