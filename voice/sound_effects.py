"""
Cybernetic Holographic Sound Synthesizer for P.H.A.S.S Sphere / J.A.R.V.I.S.
Generates futuristic sound effects (Arc-Reactor power-up, sonar radar pings,
security alerts, task completion chimes) using native Windows audio synthesis.
"""

from __future__ import annotations
import math
import struct
import sys
import threading
import time
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("phass.voice.sound_effects")


class CyberneticSoundSynthesizer:
    def __init__(self):
        self.is_enabled = True

    def play_sound(self, sound_name: str, async_play: bool = True) -> None:
        """
        Plays a synthesized cybernetic sound effect.
        """
        if not self.is_enabled:
            return

        s_clean = sound_name.strip().upper()

        if async_play:
            threading.Thread(target=self._play_direct, args=(s_clean,), daemon=True).start()
        else:
            self._play_direct(s_clean)

    def _play_direct(self, sound_name: str) -> None:
        if sys.platform != "win32":
            return

        try:
            import winsound

            if "ARC_REACTOR" in sound_name or "BOOT" in sound_name:
                # Rising frequency power-up
                for f in range(400, 1600, 150):
                    winsound.Beep(f, 35)
                winsound.Beep(1800, 120)

            elif "SONAR" in sound_name or "PING" in sound_name:
                # High-tech Sonar radar chirp
                winsound.Beep(2400, 80)
                winsound.Beep(1800, 140)

            elif "ALERT" in sound_name or "SECURITY" in sound_name or "LOCKDOWN" in sound_name:
                # Dual-tone tactical alert
                for _ in range(2):
                    winsound.Beep(1200, 100)
                    winsound.Beep(800, 100)

            elif "COMPLETE" in sound_name or "SUCCESS" in sound_name:
                # Harmonious completion chord
                winsound.Beep(987, 80)   # B5
                winsound.Beep(1318, 90)  # E6
                winsound.Beep(1975, 140) # B6

            elif "BEEP" in sound_name or "MIC" in sound_name or "WAKE" in sound_name:
                # Soft acknowledgement chirp
                winsound.Beep(1760, 60)
                winsound.Beep(2200, 80)

            else:
                # Default subtle chime
                winsound.Beep(1400, 70)

        except Exception as e:
            logger.debug(f"Audio beep not available on this terminal/session: {e}")

    def toggle_sounds(self, enabled: Optional[bool] = None) -> bool:
        if enabled is None:
            self.is_enabled = not self.is_enabled
        else:
            self.is_enabled = enabled
        return self.is_enabled


sound_synth = CyberneticSoundSynthesizer()
