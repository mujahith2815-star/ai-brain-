"""
Custom Voice Tones, Personas, and Sound FX Pack Engine for P.H.A.S.S Sphere v5.0.
Provides voice speed/rate customization, pitch modes, selectable voice personas,
and high-fidelity sound effect synthesis.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from voice.speech_engine import voice_engine
from voice.sound_effects import sound_synth

logger = logging.getLogger("phass.voice.voice_customizer")


class VoicePersonaType(str, Enum):
    BRITISH_BUTLER = "BRITISH_EXECUTIVE_BUTLER"
    CYBER_ANDROID = "CRISP_CYBER_ANDROID"
    DEEP_SENTINEL = "DEEP_CINEMATIC_SENTINEL"
    FAST_DEVELOPER = "HYPER_SPEED_DEVELOPER"


@dataclass
class VoiceProfile:
    persona: VoicePersonaType
    speech_rate_wpm: int
    volume_pct: int
    pitch_mode: str
    sound_fx_pack: str
    tagline: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona": self.persona.value,
            "speech_rate_wpm": self.speech_rate_wpm,
            "volume_pct": self.volume_pct,
            "pitch_mode": self.pitch_mode,
            "sound_fx_pack": self.sound_fx_pack,
            "tagline": self.tagline,
        }


class VoiceCustomizerEngine:
    PERSONA_PRESETS: Dict[VoicePersonaType, VoiceProfile] = {
        VoicePersonaType.BRITISH_BUTLER: VoiceProfile(
            persona=VoicePersonaType.BRITISH_BUTLER,
            speech_rate_wpm=175,
            volume_pct=100,
            pitch_mode="REFINED_ELOQUENT",
            sound_fx_pack="IRON_MAN_ARC_REACTOR",
            tagline="At your command, sir. Ready for executive operations.",
        ),
        VoicePersonaType.CYBER_ANDROID: VoiceProfile(
            persona=VoicePersonaType.CYBER_ANDROID,
            speech_rate_wpm=190,
            volume_pct=95,
            pitch_mode="SYNTHETIC_CRISP",
            sound_fx_pack="CYBERPUNK_MATRIX",
            tagline="Neural substrate online. Computing optimal execution path.",
        ),
        VoicePersonaType.DEEP_SENTINEL: VoiceProfile(
            persona=VoicePersonaType.DEEP_SENTINEL,
            speech_rate_wpm=150,
            volume_pct=100,
            pitch_mode="DEEP_RESONANT",
            sound_fx_pack="TACTICAL_RADAR",
            tagline="Perimeter secured. All defensive subsystems armed.",
        ),
        VoicePersonaType.FAST_DEVELOPER: VoiceProfile(
            persona=VoicePersonaType.FAST_DEVELOPER,
            speech_rate_wpm=220,
            volume_pct=90,
            pitch_mode="RAPID_TELEMETRY",
            sound_fx_pack="QUANTUM_DATA_STREAM",
            tagline="Hot-code compiler active. Zero latency mode engaged.",
        ),
    }

    def __init__(self):
        self.current_profile = self.PERSONA_PRESETS[VoicePersonaType.BRITISH_BUTLER]

    def set_persona(self, persona_key: str) -> VoiceProfile:
        """Sets the active voice persona."""
        p_clean = persona_key.lower().replace(" ", "_")
        selected = VoicePersonaType.BRITISH_BUTLER

        if "cyber" in p_clean or "android" in p_clean:
            selected = VoicePersonaType.CYBER_ANDROID
        elif "sentinel" in p_clean or "deep" in p_clean or "cinematic" in p_clean:
            selected = VoicePersonaType.DEEP_SENTINEL
        elif "fast" in p_clean or "developer" in p_clean or "speed" in p_clean:
            selected = VoicePersonaType.FAST_DEVELOPER
        else:
            selected = VoicePersonaType.BRITISH_BUTLER

        self.current_profile = self.PERSONA_PRESETS[selected]
        voice_engine.set_rate(self.current_profile.speech_rate_wpm)
        voice_engine.set_volume(self.current_profile.volume_pct / 100.0)
        sound_synth.play_sound("ARC_REACTOR_BOOT")
        logger.info(f"Switched voice persona to [{selected.value}] (Rate: {self.current_profile.speech_rate_wpm} wpm)")
        return self.current_profile

    def set_speech_rate(self, rate_wpm: int) -> int:
        """Sets the speech rate in words per minute (e.g. 100 to 300 wpm)."""
        clamped = max(80, min(300, rate_wpm))
        self.current_profile.speech_rate_wpm = clamped
        voice_engine.set_rate(clamped)
        return clamped

    def set_speech_volume(self, volume_pct: int) -> int:
        """Sets the speech volume percentage (0 to 100%)."""
        clamped = max(0, min(100, volume_pct))
        self.current_profile.volume_pct = clamped
        voice_engine.set_volume(clamped / 100.0)
        return clamped

    def trigger_sound_effect(self, sound_name: str) -> str:
        """Plays a high-fidelity sci-fi sound effect."""
        name_clean = sound_name.upper().replace(" ", "_")
        sound_synth.play_sound(name_clean if name_clean in sound_synth.SOUNDS else "ARC_REACTOR_BOOT")
        return f"Triggered sound effect: '{name_clean}'"

    def format_voice_status_text(self) -> str:
        return (
            f"=== P.H.A.S.S VOICE CUSTOMIZER & SOUND PACK TELEMETRY ===\n"
            f"Active Persona:     {self.current_profile.persona.value}\n"
            f"Speech Cadence:     {self.current_profile.speech_rate_wpm} Words Per Minute\n"
            f"Output Volume:      {self.current_profile.volume_pct}%\n"
            f"Pitch & Resonance:  {self.current_profile.pitch_mode}\n"
            f"Sound FX Suite:     {self.current_profile.sound_fx_pack}\n"
            f"Persona Motto:      \"{self.current_profile.tagline}\""
        )


voice_customizer = VoiceCustomizerEngine()
