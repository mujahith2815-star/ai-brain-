"""
Conversation Buffer for P.H.A.S.S / JARVIS.
Maintains multi-turn context, records interaction history,
and dynamically generates proactive follow-up queries.
"""

from __future__ import annotations
import time
from typing import Dict, Any, List, Optional
from core.personality_matrix import personality_matrix

# Global Pending Action Context Buffer for Proactive Interrupts
pending_proactive_action: Optional[Dict[str, Any]] = None
awaiting_confirmation: bool = False


class ConversationBuffer:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.turns: List[Dict[str, Any]] = []
        self.interruptions: List[str] = []
        self.pending_proactive_action: Optional[Dict[str, Any]] = None
        self.awaiting_confirmation: bool = False

    def set_pending_action(self, action: Dict[str, Any]):
        """Sets a pending proactive action and flags awaiting_confirmation."""
        global pending_proactive_action, awaiting_confirmation
        self.pending_proactive_action = action
        self.awaiting_confirmation = True
        pending_proactive_action = action
        awaiting_confirmation = True

    def clear_pending_action(self):
        """Clears any pending proactive action and resets awaiting_confirmation."""
        global pending_proactive_action, awaiting_confirmation
        self.pending_proactive_action = None
        self.awaiting_confirmation = False
        pending_proactive_action = None
        awaiting_confirmation = False

    def get_pending_action(self) -> Optional[Dict[str, Any]]:
        """Returns the current pending proactive action."""
        global pending_proactive_action
        return self.pending_proactive_action or pending_proactive_action

    def inject_interruption(self, message: str):
        """Injects an asynchronous proactive interruption into the buffer."""
        self.interruptions.append(message)

    def get_pending_interruptions(self, clear: bool = True) -> List[str]:
        """Returns any pending proactive interruptions, optionally clearing the queue."""
        res = list(self.interruptions)
        if clear:
            self.interruptions.clear()
        return res

    def has_pending_interruptions(self) -> bool:
        return len(self.interruptions) > 0

    def add_turn(self, user_query: str, assistant_response: str, action_type: str = "general"):
        """Record a completed conversation turn."""
        turn = {
            "user": user_query,
            "assistant": assistant_response,
            "action_type": action_type,
            "timestamp": time.time(),
        }
        self.turns.append(turn)
        if len(self.turns) > self.max_turns:
            self.turns.pop(0)

    def get_last_turn(self) -> Optional[Dict[str, Any]]:
        """Return the most recent conversation turn."""
        return self.turns[-1] if self.turns else None

    def get_next_follow_up(self, action_type: str = "general", persona_key: Optional[str] = None) -> str:
        """Generates a proactive follow-up prompt based on active persona and action type."""
        return personality_matrix.format_follow_up(action_type=action_type, persona_key=persona_key)

    def clear(self):
        """Clears all turns, interruptions, and pending actions in the buffer."""
        self.turns.clear()
        self.interruptions.clear()
        self.clear_pending_action()


# Global singleton
conversation_buffer = ConversationBuffer()


def set_pending_action(action: Dict[str, Any]):
    """Module-level helper to set a pending proactive action."""
    conversation_buffer.set_pending_action(action)


def clear_pending_action():
    """Module-level helper to clear pending proactive actions."""
    conversation_buffer.clear_pending_action()


def get_pending_action() -> Optional[Dict[str, Any]]:
    """Module-level helper to retrieve pending proactive action."""
    return conversation_buffer.get_pending_action()