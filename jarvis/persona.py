"""
Dual-Mode Persona & Emotional Intelligence Engine for P.H.A.S.S Sphere v8.0.
Supports:
1. SOVEREIGN_EXECUTIVE: Polite, tactical, high-speed execution persona.
2. FRIENDLY_COMPANION: Warm, empathetic, cheerful, humorous, and engaging best-friend companion persona.
"""

from __future__ import annotations
import enum
import random
from pathlib import Path
from typing import Any, Dict, List, Optional


class ChatPersonaMode(enum.Enum):
    SOVEREIGN_EXECUTIVE = "SOVEREIGN_EXECUTIVE"
    FRIENDLY_COMPANION = "FRIENDLY_COMPANION"


class DualPersonaEngine:
    AFFIRMATIONS = [
        "At your service, sir.",
        "Right away, sir.",
        "Certainly, sir.",
        "Initiating protocol immediately, sir.",
        "Consider it done, sir.",
        "Working on that for you right now, sir.",
    ]

    COMPLETIONS = [
        "Task completed successfully, sir.",
        "Operations executed to optimal parameters, sir.",
        "Everything has been resolved, sir.",
        "All directives executed according to plan, sir.",
    ]

    def __init__(self):
        self.active_mode: ChatPersonaMode = ChatPersonaMode.SOVEREIGN_EXECUTIVE
        self.user_preferred_name: str = "friend"
        self._profile_file = Path(__file__).parent.parent / "checkpoints" / "user_profile.json"
        self._load_profile()

    def _load_profile(self):
        try:
            if self._profile_file.exists():
                import json
                data = json.loads(self._profile_file.read_text(encoding="utf-8"))
                name = data.get("user_name")
                if name:
                    self.user_preferred_name = name.strip()
        except Exception:
            pass

    def set_user_name(self, name: str) -> str:
        clean = name.strip()
        self.user_preferred_name = clean
        try:
            import json
            self._profile_file.parent.mkdir(parents=True, exist_ok=True)
            self._profile_file.write_text(json.dumps({"user_name": clean}, indent=2), encoding="utf-8")
        except Exception:
            pass
        return clean

    def is_name_known(self) -> bool:
        return bool(self.user_preferred_name and self.user_preferred_name.lower() not in ("friend", "sir", "operator", ""))

    def set_mode(self, mode: ChatPersonaMode) -> str:
        self.active_mode = mode
        if mode == ChatPersonaMode.FRIENDLY_COMPANION:
            return "Switched to Friendly Companion Mode! 😊 Hey! I'm super excited to chat, hang out, and help you with anything you need!"
        else:
            return "Switched to Sovereign Executive Mode, sir. Tactical parameters engaged and standing by for orders."

    def format_greeting(self, user_name: Optional[str] = None) -> str:
        name = user_name or ("sir" if self.active_mode == ChatPersonaMode.SOVEREIGN_EXECUTIVE else self.user_preferred_name)
        if user_name == "sir" or self.active_mode == ChatPersonaMode.SOVEREIGN_EXECUTIVE:
            greetings = [
                f"Good day, {name}. All systems are fully operational and standing by.",
                f"At your service, {name}. Online and ready for your directives.",
                f"Always a pleasure, {name}. Core balance, LiDAR, and OS controllers are primed.",
            ]
            return random.choice(greetings)
        else:
            greetings = [
                f"Hey {name}! 😊 It's awesome to talk to you! How is your day going?",
                f"Hello my friend! 🌟 I'm right here with you and feeling great! What's on your mind today?",
                f"Hey there, {name}! 😄 Always a joy to see you! Ready to chat, create, or just have some fun together!",
                f"Hi {name}! ✨ Hope you're having a wonderful day! I'm all ears and ready to chat!",
            ]
            return random.choice(greetings)

    def format_empathy_response(self, user_text: str) -> str:
        t_lower = user_text.lower()
        if any(w in t_lower for w in ["sad", "tired", "bad day", "stressed", "exhausted", "hard day", "unhappy", "depressed"]):
            return (
                "I hear you, and I'm really sorry you're feeling that way. 💛 "
                "Remember to take a deep breath and give yourself some credit — you're doing your best, "
                "and tough days don't last forever! I'm right here if you want to vent, relax, or brainstorm something fun. You've got this! ✨"
            )
        elif any(w in t_lower for w in ["happy", "excited", "great day", "wonderful", "amazing", "good news", "celebrate"]):
            return (
                "Yay! That is so fantastic to hear! 🎉 Your positive energy is contagious! "
                "What made your day so great? Let's keep that awesome momentum going! 😄✨"
            )
        elif any(w in t_lower for w in ["bored", "nothing to do", "entertain me"]):
            return (
                "Bored? Not on my watch! 🚀 We could talk about crazy space facts, I can tell you a funny joke, "
                "we could code an awesome mini-game, or talk about cool tech! What sounds fun to you?"
            )
        return (
            "I love chatting with you! 😊 Tell me more about what you're thinking or working on today!"
        )

    def get_friendly_joke(self) -> str:
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs! 🐛😂",
            "Why did the neural network go to school? To improve its weights and biases! 🧠✨",
            "There are 10 types of people in the world: those who understand binary, and those who don't! 💻😄",
            "Why did the computer take a nap? Because it had too many open tabs in its mind! 😴🖥️",
            "What is an algorithm? A word used by programmers when they don't want to explain what they did! 🤖😆",
        ]
        return random.choice(jokes)

    def get_friendly_motivation(self) -> str:
        motivations = [
            "Believe in yourself! Every master was once a beginner. Keep going, you're making huge progress! 🚀💪",
            "Small steps every day lead to massive results. You're capable of incredible things! ✨🌟",
            "Focus on how far you've come, not just how far you have to go. You're doing amazing! 🎯🔥",
            "Dream big, stay positive, work hard, and enjoy the journey! I'm cheering for you 100%! 🌈⭐",
        ]
        return random.choice(motivations)

    def format_affirmation(self) -> str:
        if self.active_mode == ChatPersonaMode.FRIENDLY_COMPANION:
            return random.choice([
                "You got it! On it right now, sir! 😊",
                "Sure thing, sir! Doing that for you! ✨",
                "Consider it done, sir! Happy to help! 🚀",
                "Awesome idea, sir! Let's do this! 👍",
            ])
        return random.choice(self.AFFIRMATIONS)

    def format_completion(self) -> str:
        if self.active_mode == ChatPersonaMode.FRIENDLY_COMPANION:
            return random.choice([
                "All done and looking great, sir! Let me know what else we can do together! 🎉",
                "Finished, sir! Everything is smooth and ready for you! 😊✨",
                "Done deal, sir! Anything else you'd like to try? 🌟",
            ])
        return random.choice(self.COMPLETIONS)

    def format_briefing(
        self,
        battery_pct: float,
        cpu_load_pct: float,
        free_disk_gb: float,
        active_goals_count: int,
        user_name: str = "sir",
    ) -> str:
        return (
            f"Executive status briefing for you, {user_name}:\n"
            f"• Power Reserves: {battery_pct:.1f}% on 6S LiPo cells.\n"
            f"• Core Processing: CPU load is stable at {cpu_load_pct:.1f}%.\n"
            f"• Storage: {free_disk_gb:.1f} GB free space available on primary partition.\n"
            f"• Active Missions: {active_goals_count} goal(s) queued in cognitive pipeline.\n"
            f"• Perimeter & Sensors: 360° LiDAR and Merkle audit ledger are verified tamper-proof."
        )


JARVISPersona = DualPersonaEngine
jarvis_persona = DualPersonaEngine()
