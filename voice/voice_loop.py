"""
Voice Interaction Loop Orchestrator for Orvix Sphere.
Continuously loops:
WakeWordDetector.wait_for_wake_word() -> SpeechRecognizer.listen_and_transcribe() -> agent.run() -> SpeechSynthesizer.speak()
Logs interactions to KnowledgeStore.
"""

import sys
import time
import logging
import threading
from typing import Optional, Any, Callable

from config.voice_config import VoiceConfig, voice_config
from voice.speech_to_text import SpeechRecognizer
from voice.text_to_speech import SpeechSynthesizer
from voice.wake_word import WakeWordDetector

logger = logging.getLogger("orvix.voice.voice_loop")


def _safe_print(text: str):
    try:
        print(text)
    except Exception:
        try:
            enc = sys.stdout.encoding or "utf-8"
            clean = text.encode(enc, errors="replace").decode(enc, errors="replace")
            print(clean)
        except Exception:
            pass


class VoiceLoop:
    """
    Hands-free voice interaction loop connecting Wake Word, STT, Agent Reasoning, and TTS.
    """

    def __init__(
        self,
        agent: Optional[Any] = None,
        config: Optional[VoiceConfig] = None,
        recognizer: Optional[SpeechRecognizer] = None,
        synthesizer: Optional[SpeechSynthesizer] = None,
        wake_detector: Optional[WakeWordDetector] = None,
        knowledge_store: Optional[Any] = None,
    ):
        self.config = config or voice_config
        self.recognizer = recognizer or SpeechRecognizer(config=self.config)
        self.synthesizer = synthesizer or SpeechSynthesizer(
            rate=self.config.tts_rate,
            volume=self.config.tts_volume,
            voice_id=self.config.tts_voice_id
        )
        self.wake_detector = wake_detector or WakeWordDetector(config=self.config)
        self.agent = agent
        self.knowledge_store = knowledge_store
        self._running = False
        self._thread: Optional[threading.Thread] = None

        if self.knowledge_store is None and self.config.log_to_knowledge_store:
            try:
                from knowledge.sqlite_store import KnowledgeStore
                self.knowledge_store = KnowledgeStore()
            except Exception as e:
                logger.debug(f"KnowledgeStore init notice: {e}")

    def _resolve_agent(self) -> Any:
        if self.agent is not None:
            return self.agent
        try:
            from core.llama_tool_agent import llama_tool_agent
            self.agent = llama_tool_agent
            return self.agent
        except Exception as e:
            logger.warning(f"Could not import llama_tool_agent: {e}")
            return None

    def _execute_agent(self, query: str) -> str:
        agent = self._resolve_agent()
        if agent is None:
            return "I heard your request, but the cognitive agent brain is currently offline."

        try:
            if hasattr(agent, "run"):
                res = agent.run(query)
                if hasattr(res, "final_response"):
                    return res.final_response
                return str(res)
            elif hasattr(agent, "process_query"):
                return str(agent.process_query(query))
            elif callable(agent):
                return str(agent(query))
            return str(agent)
        except Exception as e:
            logger.error(f"Error executing agent query '{query}': {e}")
            return f"An error occurred while processing your request: {e}"

    def _log(self, role: str, content: str):
        if self.knowledge_store and self.config.log_to_knowledge_store:
            try:
                self.knowledge_store.log_conversation(
                    session_id="voice_session",
                    role=role,
                    content=content
                )
            except Exception as e:
                logger.debug(f"Could not log conversation: {e}")

    def step(
        self,
        text_input_fallback: Optional[str] = None,
        mock_wake: bool = False
    ) -> Optional[str]:
        """
        Executes a single voice turn:
        1. Wait for wake word
        2. Record & transcribe speech
        3. Fallback to text if no mic
        4. Run agent
        5. Speak answer & log
        Returns the agent response text or None.
        """
        if not mock_wake:
            triggered = self.wake_detector.wait_for_wake_word(timeout=self.config.wake_word_timeout)
            if not triggered:
                return None

        _safe_print("\n[Voice] Wake word detected ('" + self.config.wake_word + "').")

        user_query = None
        if text_input_fallback is not None:
            user_query = text_input_fallback
        elif self.recognizer.is_microphone_available():
            _safe_print("[Voice] Listening for your command...")
            user_query = self.recognizer.listen_and_transcribe(timeout=self.config.listen_timeout)

        if not user_query:
            if self.config.fallback_to_text:
                _safe_print("[Voice] Microphone unavailable or no audio detected. Text fallback active.")
                try:
                    user_query = input("Voice Command (text fallback) >> ").strip()
                except (EOFError, KeyboardInterrupt):
                    return None

        if not user_query:
            _safe_print("[Voice] No query provided. Returning to standby.")
            return None

        _safe_print("\n[Voice User] >> " + str(user_query))
        self._log("user", user_query)

        # Process through agent
        response = self._execute_agent(user_query)
        _safe_print("[Orvix] >> " + str(response) + "\n")
        self._log("assistant", response)

        # Speak response
        if self.config.voice_enabled:
            self.synthesizer.speak(response, block=False)

        return response

    def run(self):
        """Runs the loop indefinitely until Ctrl+C."""
        self._running = True
        _safe_print("\n" + "="*60)
        _safe_print("      ORVIX SPHERE — HANDS-FREE VOICE INTERFACE ONLINE       ")
        _safe_print("="*60)
        _safe_print("[*] Wake Word:     '" + self.config.wake_word + "' (or " + self.config.keyboard_fallback_hotkey.upper() + ")")
        _safe_print("[*] Whisper Model: " + self.config.whisper_model + " (CPU)")
        _safe_print("[*] TTS Engine:    pyttsx3 (Rate: " + str(self.config.tts_rate) + " WPM)")
        _safe_print("[*] Press Ctrl+C at any time to exit voice mode.\n")

        try:
            while self._running:
                self.step()
        except KeyboardInterrupt:
            _safe_print("\n[*] Voice loop stopped by operator (Ctrl+C).")
        finally:
            self.stop()

    def start(self):
        """Starts the voice loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self.run, daemon=True, name="VoiceLoop-Thread")
        self._thread.start()

    def stop(self):
        """Stops the loop and releases resources."""
        self._running = False
        self.wake_detector.stop()
        self.synthesizer.stop()
