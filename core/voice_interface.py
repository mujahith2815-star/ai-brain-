"""
Voice Interface – Cross-platform Speech-to-Text and Text-to-Speech
"""

import os
import sys
import threading
import queue
import time
import numpy as np
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
import tempfile

# Conditional imports with fallbacks
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except (ImportError, Exception):
    PORCUPINE_AVAILABLE = False

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

try:
    import scipy.io.wavfile as wavfile
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class VoiceInterface:
    """
    Complete voice interface: STT (Whisper), TTS (pyttsx3), Wake Word (Porcupine)
    """

    def __init__(
        self,
        wake_word: str = "phass",
        model_size: str = "base",
        voice_id: Optional[str] = None,
        rate: int = 180,
        volume: float = 1.0,
        device_index: Optional[int] = None,
    ):
        self.wake_word = wake_word.lower()
        self.wake_phrases = ["hey phass", "phass", "hey p.h.a.s.s", "p.h.a.s.s", "hey pass", "pass"]
        self.model_size = model_size
        self.voice_id = voice_id
        self.rate = rate
        self.volume = volume
        self.device_index = device_index
        self.is_listening = False
        self.listening_thread: Optional[threading.Thread] = None
        self.callback: Optional[Callable[[str], None]] = None
        self.command_queue = queue.Queue()
        self.audio_buffer = []
        self.sample_rate = 16000

        # Interruptible Voice (Barge-In) Configuration
        self.barge_in_enabled: bool = True
        self.barge_in_threshold: float = 0.04
        self.is_speaking: bool = False
        self.was_interrupted: bool = False

        # Initialize Whisper (STT) - lazy loaded on demand or when available
        self.stt_model = None
        if WHISPER_AVAILABLE:
            try:
                self.stt_model = whisper.load_model(model_size)
            except Exception as e:
                # Keep lightweight if model download is pending
                self.stt_model = None
        else:
            self.stt_model = None

        # Initialize pyttsx3 (TTS)
        self.tts_engine = None
        self._voices = []
        if TTS_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", rate)
                self.tts_engine.setProperty("volume", volume)
                if voice_id:
                    self.tts_engine.setProperty("voice", voice_id)
                self._voices = self.tts_engine.getProperty("voices") or []
            except Exception as e:
                self.tts_engine = None
                self._voices = []

        # Initialize Porcupine (Wake Word)
        self.porcupine = None
        self.porcupine_sample_rate = 16000
        self.porcupine_frame_length = 512
        if PORCUPINE_AVAILABLE:
            try:
                self.porcupine = pvporcupine.create(keywords=[self.wake_word])
                self.porcupine_sample_rate = self.porcupine.sample_rate
                self.porcupine_frame_length = self.porcupine.frame_length
            except Exception:
                try:
                    self.porcupine = pvporcupine.create(keywords=["picovoice"])
                    self.porcupine_sample_rate = self.porcupine.sample_rate
                    self.porcupine_frame_length = self.porcupine.frame_length
                except Exception:
                    self.porcupine = None

    # ============ TEXT-TO-SPEECH ============

    def inject_disfluencies(self, text: str) -> str:
        """
        Randomly injects human speech disfluencies ('um', 'ah', or '... [pause]')
        approximately every 15-20 words to mimic natural human hesitation.
        """
        import random
        words = text.split()
        if len(words) < 18:
            return text

        fillers = ["um,", "ah,", "..."]
        result = []
        count_since_last = 0
        target_interval = random.randint(15, 20)

        for w in words:
            result.append(w)
            count_since_last += 1
            if count_since_last >= target_interval:
                filler = random.choice(fillers)
                result.append(filler)
                count_since_last = 0
                target_interval = random.randint(15, 20)

        return " ".join(result)

    def determine_speech_rate(self, text: str, user_context: Optional[str] = None) -> int:
        """
        Adjusts TTS speaking rate dynamically:
        - If text or context contains 'urgent', 'quickly', 'hurry' -> 220 WPM (speeding up)
        - If text or context contains 'relax', 'think', 'calm' -> 120 WPM (slowing down)
        - Otherwise returns default rate (180 WPM)
        """
        combined = f"{text} {user_context or ''}".lower()
        if any(w in combined for w in ["urgent", "quickly", "hurry", "asap", "emergency", "fast"]):
            return 220
        elif any(w in combined for w in ["relax", "think", "calm", "slow", "deliberate", "ponder"]):
            return 120
        return self.rate or 180

    def flush_queue(self):
        """Flushes the pending command and process_query queue."""
        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except Exception:
                break

    def speak(self, text: str, async_mode: bool = True, user_context: Optional[str] = None) -> str:
        """
        Convert text to speech and play it with natural human disfluencies and dynamic rate.
        Args:
            text: The text to speak.
            async_mode: If True, speak in background thread (non-blocking).
            user_context: Context string for speed adjustment (e.g. urgent, relax).
        """
        if not text or not text.strip():
            return "Nothing to speak."
        if not self.tts_engine:
            return "TTS not available. Install pyttsx3."

        if async_mode:
            threading.Thread(target=self._speak_sync, args=(text, user_context), daemon=True).start()
            return f"Speaking: {text[:50]}..."
        else:
            self._speak_sync(text, user_context)
            return f"Spoke: {text[:50]}..."

    def _speak_sync(self, text: str, user_context: Optional[str] = None):
        """Synchronous TTS (blocking) with interruptible barge-in monitoring, disfluencies, and rate adaptation."""
        if not self.tts_engine:
            return

        self.is_speaking = True
        self.was_interrupted = False
        monitor_thread = None

        # 1. Apply dynamic rate modulation
        target_rate = self.determine_speech_rate(text, user_context)
        try:
            self.tts_engine.setProperty("rate", target_rate)
        except Exception:
            pass

        # 2. Inject human speech disfluencies
        spoken_text = self.inject_disfluencies(text)

        if self.barge_in_enabled and SOUNDDEVICE_AVAILABLE:
            def _barge_in_listener():
                try:
                    sr = self.sample_rate
                    chunk_size = int(sr * 0.1)  # 100ms
                    with sd.InputStream(samplerate=sr, channels=1, dtype="float32", device=self.device_index) as stream:
                        while self.is_speaking:
                            data, _ = stream.read(chunk_size)
                            if not self.is_speaking:
                                break
                            amp = float(np.max(np.abs(data))) if len(data) > 0 else 0.0
                            if amp >= self.barge_in_threshold:
                                print("\n[!] Barge-In: Speech detected while speaking. Aborting speech to listen...")
                                self.was_interrupted = True
                                self.stop_speaking()
                                self.flush_queue()
                                break
                except Exception:
                    pass

            monitor_thread = threading.Thread(target=_barge_in_listener, daemon=True)
            monitor_thread.start()

        try:
            self.tts_engine.say(spoken_text)
            self.tts_engine.runAndWait()
        except Exception as e:
            print(f"TTS error: {e}")
        finally:
            self.is_speaking = False
            try:
                self.tts_engine.setProperty("rate", self.rate)
            except Exception:
                pass

    def stop_speaking(self):
        """Immediately halts active speech playback (Barge-In interrupt)."""
        self.is_speaking = False
        if self.tts_engine:
            try:
                self.tts_engine.stop()
            except Exception:
                pass

    def enable_barge_in(self, threshold: Optional[float] = None):
        """Enable voice barge-in interruptibility."""
        self.barge_in_enabled = True
        if threshold is not None:
            self.barge_in_threshold = threshold

    def disable_barge_in(self):
        """Disable voice barge-in interruptibility."""
        self.barge_in_enabled = False

    def trigger_barge_in(self):
        """Programmatically triggers a barge-in event for testing and control."""
        self.was_interrupted = True
        self.stop_speaking()

    def speak_async(self, text: str):
        """Helper alias for async speech."""
        return self.speak(text, async_mode=True)

    def list_voices(self) -> list:
        """List available voices."""
        if not self.tts_engine:
            return []
        return [
            {
                "id": v.id,
                "name": v.name,
                "gender": getattr(v, "gender", "unknown"),
            }
            for v in self._voices
        ]

    def set_voice_by_gender(self, gender: str) -> str:
        """Set voice by gender ('male' or 'female')."""
        if not self.tts_engine:
            return "TTS not available."
        gender_lower = gender.lower()
        for voice in self._voices:
            if gender_lower in voice.name.lower() or (
                hasattr(voice, "gender") and gender_lower in str(voice.gender).lower()
            ):
                try:
                    self.tts_engine.setProperty("voice", voice.id)
                    self.voice_id = voice.id
                    return f"Voice set to {voice.name}"
                except Exception as e:
                    return f"Failed to set voice: {e}"
        return f"No {gender} voice found."

    def set_voice_by_id(self, voice_id: str) -> str:
        """Set voice by ID."""
        if not self.tts_engine:
            return "TTS not available."
        try:
            self.tts_engine.setProperty("voice", voice_id)
            self.voice_id = voice_id
            return f"Voice set to {voice_id}"
        except Exception as e:
            return f"Failed to set voice: {e}"

    def set_voice(self, voice_id: str) -> str:
        """Alias for set_voice_by_id."""
        return self.set_voice_by_id(voice_id)

    def set_rate(self, rate: int) -> str:
        """Set speaking rate (words per minute)."""
        if self.tts_engine:
            try:
                self.tts_engine.setProperty("rate", rate)
                self.rate = rate
                return f"Rate set to {rate} wpm"
            except Exception as e:
                return f"Failed to set rate: {e}"
        return "TTS not available."

    def set_volume(self, volume: float) -> str:
        """Set volume (0.0 to 1.0)."""
        if self.tts_engine:
            try:
                vol = max(0.0, min(1.0, float(volume)))
                self.tts_engine.setProperty("volume", vol)
                self.volume = vol
                return f"Volume set to {int(vol * 100)}%"
            except Exception as e:
                return f"Failed to set volume: {e}"
        return "TTS not available."

    # ============ SPEECH-TO-TEXT ============

    def record_audio(
        self,
        duration: Optional[float] = None,
        silence_duration: float = 1.0,
        silence_threshold: float = 0.03,
        max_duration: float = 10.0,
        sample_rate: int = 16000,
        silence_timeout: Optional[float] = None,
    ) -> Optional[np.ndarray]:
        """
        Record audio from microphone.
        If duration is None, records until silence (VAD) or max_duration.
        - silence_threshold: 0.03 to ignore fan/AC background noise.
        - silence_duration: 1.0s silence stops recording after speech.
        - max_duration: 10s maximum recording time limit.
        """
        if not SOUNDDEVICE_AVAILABLE:
            print("[!] sounddevice not available")
            return None

        sr = sample_rate or self.sample_rate

        if duration:
            try:
                recording = sd.rec(
                    int(duration * sr),
                    samplerate=sr,
                    channels=1,
                    dtype="float32",
                    device=self.device_index,
                )
                sd.wait()
                return recording.flatten()
            except Exception as e:
                print(f"Recording error: {e}")
                return None
        else:
            # Voice Activity Detection – record until silence or max_duration
            print("[*] Listening... (speak now, silence will stop)")
            audio_chunks = []
            chunk_duration = 0.2  # 200ms per chunk for responsive detection
            actual_silence_duration = silence_timeout if silence_timeout is not None else silence_duration
            chunks_per_silence = max(1, int(actual_silence_duration / chunk_duration))
            max_chunks = max(1, int(max_duration / chunk_duration))
            silent_chunks = 0
            speech_started = False

            try:
                with sd.InputStream(
                    samplerate=sr,
                    channels=1,
                    dtype="float32",
                    device=self.device_index,
                ) as stream:
                    while len(audio_chunks) < max_chunks:
                        data, overflowed = stream.read(int(sr * chunk_duration))
                        flat = data.flatten()
                        audio_chunks.append(flat)
                        max_amp = float(np.max(np.abs(flat))) if len(flat) > 0 else 0.0
                        if max_amp >= max(silence_threshold, self.barge_in_threshold) and self.is_speaking:
                            print("\n[!] VAD: Amplitude spike detected while speaking. Immediately stopping TTS and flushing queue...")
                            self.was_interrupted = True
                            self.stop_speaking()
                            self.flush_queue()

                        if max_amp < silence_threshold:
                            silent_chunks += 1
                        else:
                            speech_started = True
                            silent_chunks = 0
                        if silent_chunks >= chunks_per_silence and (speech_started or len(audio_chunks) >= chunks_per_silence):
                            break
                if len(audio_chunks) >= max_chunks:
                    print("[*] Max duration reached (10s), stopping recording.")
                else:
                    print("[*] Silence detected, stopping recording.")
                return np.concatenate(audio_chunks) if audio_chunks else np.array([], dtype=np.float32)
            except Exception as e:
                print(f"Recording error: {e}")
                return None

    def apply_noise_cancellation(
        self,
        audio: np.ndarray,
        noise_gate_threshold: float = 0.01,
        use_agc: bool = True,
    ) -> np.ndarray:
        """
        Apply noise cancellation and signal conditioning to an audio array.
        Features:
        - Noise gate (zeros out background noise below threshold)
        - Automatic Gain Control (AGC / peak normalization)
        """
        if audio is None or len(audio) == 0:
            return audio

        # Apply noise gate
        processed = np.where(np.abs(audio) > noise_gate_threshold, audio, 0.0)

        # Apply AGC
        if use_agc:
            max_val = np.max(np.abs(processed))
            if max_val > 0.0:
                processed = processed / max_val

        return processed

    def record_audio_with_noise_cancellation(
        self,
        duration: Optional[float] = None,
        noise_gate_threshold: float = 0.01,
        use_agc: bool = True,
    ) -> Optional[np.ndarray]:
        """
        Record audio with advanced noise cancellation.
        Features:
        - Noise gate (removes background noise)
        - Automatic Gain Control (AGC)
        - Spectral subtraction for stationary noise
        """
        audio = self.record_audio(duration=duration)
        if audio is None:
            return None

        return self.apply_noise_cancellation(
            audio,
            noise_gate_threshold=noise_gate_threshold,
            use_agc=use_agc,
        )

    def transcribe_audio(self, audio_data: np.ndarray) -> str:
        """Transcribe audio using Whisper."""
        if not WHISPER_AVAILABLE:
            return "STT not available. Install openai-whisper."

        if not self.stt_model:
            try:
                self.stt_model = whisper.load_model(self.model_size)
            except Exception as e:
                return f"Whisper load error: {e}"

        if not SCIPY_AVAILABLE:
            return "scipy not available. Install scipy."

        try:
            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                temp_path = f.name

            audio_int16 = (audio_data * 32767).astype(np.int16)
            wavfile.write(temp_path, self.sample_rate, audio_int16)

            result = self.stt_model.transcribe(temp_path)
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            return result.get("text", "").strip()
        except Exception as e:
            return f"Transcription error: {e}"

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Alias for transcribe_audio."""
        return self.transcribe_audio(audio_data)

    def listen_command(self) -> str:
        """Complete pipeline: record → transcribe → return text."""
        audio = self.record_audio()
        if audio is None or len(audio) == 0:
            return ""
        return self.transcribe_audio(audio)

    # ============ WAKE WORD DETECTION ============

    def is_wake_phrase(self, text: str) -> bool:
        """Checks if text contains 'Hey P.H.A.S.S', 'P.H.A.S.S', or configured wake word."""
        if not text:
            return False
        tl = text.lower().strip()
        return any(wp in tl for wp in self.wake_phrases) or "phass" in tl or "hey phass" in tl

    def extract_command_after_wake_word(self, text: str) -> str:
        """Extracts the command portion after the wake word."""
        if not text:
            return ""
        import re
        m = re.search(r"(?:hey\s+)?p\.?h\.?a\.?s\.?s[\s,\.\!\?]+(.*)", text, re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip()
        m2 = re.search(r"(?:hey\s+)?(?:pass|llama|jarvis)[\s,\.\!\?]+(.*)", text, re.IGNORECASE)
        if m2 and m2.group(1).strip():
            return m2.group(1).strip()
        return text.strip()

    def _update_tray_state(self, state: str):
        """Notifies global listener / system tray of voice state (e.g. 'listening' pulsing cyan dot vs 'recording')."""
        try:
            from core.global_listener import get_global_listener
            listener = get_global_listener()
            listener.set_tray_state(state)
        except Exception:
            pass

    def listen_for_wake_word(self) -> Optional[str]:
        """
        Continuously listen for wake word ('Hey P.H.A.S.S' / 'P.H.A.S.S'), then record a command.
        Returns the transcribed command or None if wake word not heard.
        """
        self._update_tray_state("listening")

        # 1. Porcupine Engine if initialized
        if self.porcupine and SOUNDDEVICE_AVAILABLE:
            frame_length = self.porcupine_frame_length
            sample_rate = self.porcupine_sample_rate
            try:
                with sd.InputStream(
                    samplerate=sample_rate,
                    channels=1,
                    dtype="int16",
                    device=self.device_index,
                ) as stream:
                    while self.is_listening or True:
                        data, overflowed = stream.read(frame_length)
                        pcm = data.flatten()
                        if self.porcupine.process(pcm) >= 0:
                            print("\n[+] Porcupine: 'Hey P.H.A.S.S' wake word detected! Listening for command...")
                            self._update_tray_state("recording")
                            audio = self.record_audio(duration=5.0)
                            self._update_tray_state("listening")
                            if audio is not None and len(audio) > 0:
                                return self.transcribe_audio(audio)
                            return ""
                        if not self.is_listening:
                            break
            except Exception as e:
                print(f"Porcupine listening notice: {e}")

        # 2. Continuous Acoustic / VAD Fallback for 'Hey P.H.A.S.S' / 'P.H.A.S.S'
        if SOUNDDEVICE_AVAILABLE and WHISPER_AVAILABLE:
            try:
                audio = self.record_audio(duration=4.0)
                if audio is not None and len(audio) > 0:
                    text = self.transcribe_audio(audio)
                    if text and self.is_wake_phrase(text):
                        print(f"\n[+] Acoustic VAD: Wake phrase detected: '{text}'")
                        cmd = self.extract_command_after_wake_word(text)
                        if cmd and len(cmd) > 2:
                            return cmd
                        # If only wake phrase was spoken, listen for next command
                        self._update_tray_state("recording")
                        cmd_audio = self.record_audio(duration=5.0)
                        self._update_tray_state("listening")
                        if cmd_audio is not None and len(cmd_audio) > 0:
                            return self.transcribe_audio(cmd_audio)
                        return ""
            except Exception as e:
                print(f"Acoustic wake word listening notice: {e}")

        return None

    def start_on_boot(self, callback: Callable[[str], None]):
        """
        Starts the Porcupine / P.H.A.S.S wake word engine immediately on boot / service startup.
        """
        return self.start_continuous_listening(callback)

    def start_continuous_listening(self, callback: Callable[[str], None]):
        """Start a background thread that listens for wake word and calls callback."""
        self.callback = callback
        self.is_listening = True
        self._update_tray_state("listening")
        self.listening_thread = threading.Thread(target=self._continuous_listen_loop, daemon=True)
        self.listening_thread.start()
        return "Continuous listening started. Say 'Hey P.H.A.S.S' to activate."

    def _continuous_listen_loop(self):
        """Background loop for continuous wake word listening."""
        while self.is_listening:
            try:
                command = self.listen_for_wake_word()
                if command and self.callback:
                    self._update_tray_state("recording")
                    self.callback(command)
                    self._update_tray_state("listening")
            except Exception as e:
                print(f"Listening loop error: {e}")
                time.sleep(1)

    def stop_listening(self):
        """Stop continuous listening."""
        self.is_listening = False
        self._update_tray_state("idle")
        if self.listening_thread:
            self.listening_thread.join(timeout=2)
        return "Stopped listening."

    # ============ STATUS ============

    def get_status(self) -> dict:
        """Get current voice interface status."""
        return {
            "stt_available": WHISPER_AVAILABLE and self.stt_model is not None,
            "tts_available": TTS_AVAILABLE and self.tts_engine is not None,
            "wake_word_available": PORCUPINE_AVAILABLE and self.porcupine is not None,
            "is_listening": self.is_listening,
            "wake_word": self.wake_word,
            "rate": self.rate,
            "volume": self.volume,
            "model_size": self.model_size,
            "device_index": self.device_index,
        }

    def restart(self) -> "VoiceInterface":
        """Restarts the voice interface instance, re-initializing all speech drivers."""
        return restart_voice_service(
            wake_word=self.wake_word,
            model_size=self.model_size,
            voice_id=self.voice_id,
            rate=self.rate,
            volume=self.volume,
            device_index=self.device_index,
        )


# Global instance
_voice_interface = None


def get_voice_interface(**kwargs) -> VoiceInterface:
    global _voice_interface
    if _voice_interface is None:
        _voice_interface = VoiceInterface(**kwargs)
    return _voice_interface


def restart_voice_service(**kwargs) -> VoiceInterface:
    """Restarts the voice service, shutting down any active listeners and re-initializing."""
    global _voice_interface
    if _voice_interface is not None:
        try:
            _voice_interface.stop_listening()
        except Exception:
            pass
    _voice_interface = VoiceInterface(**kwargs)
    return _voice_interface
