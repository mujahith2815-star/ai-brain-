"""
Speech-to-Text (STT) module for Orvix Sphere using openai-whisper and sounddevice.
Provides offline local transcription with graceful fallback when no microphone is found.
"""

import logging
import threading
from typing import Optional
import numpy as np

from config.voice_config import VoiceConfig, voice_config

logger = logging.getLogger("orvix.voice.stt")


class SpeechRecognizer:
    """
    Transcribes spoken audio to text using OpenAI Whisper on local CPU.
    Gracefully handles missing microphones without crashing.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        language: Optional[str] = None,
        config: Optional[VoiceConfig] = None,
    ):
        self.config = config or voice_config
        self.model_name = model_name or self.config.whisper_model
        self.language = language or self.config.whisper_language
        self._model = None
        self._lock = threading.Lock()

    def is_microphone_available(self) -> bool:
        """
        Returns True if a recording audio input device is detected and accessible.
        """
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            for dev in devices:
                if dev.get("max_input_channels", 0) > 0:
                    return True
            return False
        except Exception as e:
            logger.debug(f"Audio device query failed: {e}")
            return False

    def _load_model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        import whisper
                        self._model = whisper.load_model(self.model_name, device="cpu")
                    except Exception as e:
                        logger.error(f"Failed to load Whisper model '{self.model_name}': {e}")
                        self._model = None
        return self._model

    def record_audio(
        self,
        duration: float = 5.0,
        sample_rate: int = 16000
    ) -> Optional[np.ndarray]:
        """
        Records `duration` seconds of audio from the default input device.
        Returns float32 1D numpy array or None if microphone is missing or recording fails.
        """
        if not self.is_microphone_available():
            return None

        try:
            import sounddevice as sd
            num_frames = int(duration * sample_rate)
            audio = sd.rec(num_frames, samplerate=sample_rate, channels=1, dtype="float32")
            sd.wait()
            audio = np.squeeze(audio)
            return audio
        except Exception as e:
            logger.warning(f"Audio recording failed: {e}")
            return None

    def transcribe_audio_array(self, audio: np.ndarray) -> Optional[str]:
        """
        Transcribes an in-memory float32 audio array using Whisper.
        Returns cleaned string or None.
        """
        if audio is None or len(audio) == 0:
            return None

        # Check silence threshold
        rms = float(np.sqrt(np.mean(audio ** 2)))
        if rms < self.config.silence_threshold:
            logger.debug(f"Audio level ({rms:.5f}) below silence threshold ({self.config.silence_threshold})")
            return None

        model = self._load_model()
        if model is None:
            return None

        try:
            audio_float = audio.astype(np.float32)
            res = model.transcribe(
                audio_float,
                fp16=False,
                language=self.language,
                task="transcribe",
                without_timestamps=True,
            )
            text = res.get("text", "").strip()
            return text if text else None
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return None

    def listen_and_transcribe(self, timeout: Optional[float] = None) -> Optional[str]:
        """
        Records from microphone for `timeout` seconds and transcribes to text.
        Returns None gracefully if no microphone is found or no speech is recognized.
        """
        duration = timeout or self.config.listen_timeout
        audio = self.record_audio(duration=duration, sample_rate=self.config.audio_sample_rate)
        if audio is None:
            return None
        return self.transcribe_audio_array(audio)
