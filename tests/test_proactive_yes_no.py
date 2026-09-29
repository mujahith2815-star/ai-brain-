"""
Unit Tests for Proactive Interrupt Confirmation & Cooldown.
Verifies:
1. Pending Action Context Buffer in core/conversation_buffer.py tracks pending actions and awaiting_confirmation.
2. route_intent() routes 'yes', 'yeah', 'sure', etc. to 'proactive_confirm' and 'no', 'cancel' to 'proactive_decline'
   when awaiting_confirmation is True.
3. process_query() executes the pending action, reports the result, and clears the buffer.
4. Proactive Monitor enforces a 5-minute cooldown on the same event_signature (e.g. 'cpu_spike_99') to prevent alert spam.
"""

import time
import pytest
from core.conversation_buffer import (
    conversation_buffer,
    set_pending_action,
    clear_pending_action,
    get_pending_action,
)
from core.proactive_monitor import proactive_monitor
from nlp.answer_pipeline import route_intent, process_query


@pytest.fixture(autouse=True)
def reset_conversation_buffer():
    """Ensure conversation buffer and pending action are cleanly reset for each test."""
    clear_pending_action()
    conversation_buffer.clear()
    yield
    clear_pending_action()
    conversation_buffer.clear()


def test_proactive_confirm_flow():
    """
    Simulates Proactive Monitor asking to inspect processes:
    - User replies 'yes'
    - Intent routes to 'proactive_confirm'
    - process_query executes inspect_processes and reports results
    - Buffer is cleared
    """
    # 1. Proactive Monitor detects CPU spike and asks user
    event_text = proactive_monitor.trigger_event(
        event_type="CPU_SPIKE",
        details="a sudden CPU spike reaching 99.8%. Would you like me to inspect running processes?",
        action={"action": "inspect_processes", "args": {"cpu_percent": 99.8}},
        event_signature=f"cpu_spike_test_{time.time()}",
    )
    assert "Would you like me to inspect running processes?" in event_text
    assert conversation_buffer.awaiting_confirmation is True
    assert conversation_buffer.pending_proactive_action is not None
    assert conversation_buffer.pending_proactive_action.get("action") == "inspect_processes"

    # 2. User replies 'yes'
    intent = route_intent("yes")
    assert intent == "proactive_confirm"

    # 3. process_query executes the confirmation
    resp = process_query("yes")
    assert "inspecting processes" in resp.lower()
    assert "high-cpu" in resp.lower() or "tasks" in resp.lower()
    assert "i didn't quite catch that" not in resp.lower()
    assert "verified reference archives" not in resp.lower()

    # 4. Verify buffer is cleared
    assert conversation_buffer.awaiting_confirmation is False
    assert conversation_buffer.pending_proactive_action is None


def test_proactive_decline_flow():
    """
    Simulates user declining a proactive interrupt:
    - User replies 'no'
    - Intent routes to 'proactive_decline'
    - process_query replies: 'Understood, sir. I'll hold off.'
    - Buffer is cleared
    """
    set_pending_action({"action": "inspect_processes", "args": {}})
    assert conversation_buffer.awaiting_confirmation is True

    intent = route_intent("no")
    assert intent == "proactive_decline"

    resp = process_query("no")
    assert resp == "Understood, sir. I'll hold off."
    assert conversation_buffer.awaiting_confirmation is False
    assert conversation_buffer.pending_proactive_action is None


def test_proactive_affirmation_and_decline_variations():
    """Verify various affirmative and negative phrasing."""
    affirmations = ["yes", "yeah", "yep", "sure", "ok", "okay", "do it", "proceed"]
    for word in affirmations:
        set_pending_action({"action": "inspect_processes"})
        assert route_intent(word) == "proactive_confirm", f"Failed for affirmation '{word}'"

    declines = ["no", "nope", "cancel", "stop", "nevermind"]
    for word in declines:
        set_pending_action({"action": "inspect_processes"})
        assert route_intent(word) == "proactive_decline", f"Failed for decline '{word}'"


def test_proactive_monitor_5_minute_cooldown():
    """
    Verifies that triggering the same event_signature within 5 minutes (300s)
    is throttled to prevent spamming the user.
    """
    sig = f"cpu_spike_cooldown_test_{time.time()}"
    
    # First alert should fire
    msg1 = proactive_monitor.trigger_event(
        event_type="CPU_SPIKE",
        details="a sudden CPU spike reaching 99.9%. Would you like me to inspect running processes?",
        action={"action": "inspect_processes"},
        event_signature=sig,
    )
    assert msg1 != ""
    assert "[P.H.A.S.S Interrupts]" in msg1

    # Second alert immediately after with same signature should be throttled
    msg2 = proactive_monitor.trigger_event(
        event_type="CPU_SPIKE",
        details="a sudden CPU spike reaching 99.9%. Would you like me to inspect running processes?",
        action={"action": "inspect_processes"},
        event_signature=sig,
    )
    assert msg2 == "", "Expected repeated event with same signature to be throttled by cooldown"

    # Different signature should fire without being blocked
    other_sig = f"usb_plug_{time.time()}"
    msg3 = proactive_monitor.trigger_event(
        event_type="USB_INSERTION",
        details="a new drive D: was plugged in.",
        event_signature=other_sig,
    )
    assert msg3 != ""
    assert "storage volume" in msg3 or "drive D:" in msg3
