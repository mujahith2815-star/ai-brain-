"""
Unit tests for the Event Bus.
"""

import pytest
import asyncio
from core.event_bus import EventBus, Event, EventType


@pytest.mark.asyncio
async def test_event_bus_publish_subscribe():
    bus = EventBus()
    received = []

    async def sample_handler(event: Event):
        received.append(event)

    bus.subscribe(EventType.GOAL_CREATED, sample_handler)

    test_event = Event(
        type=EventType.GOAL_CREATED,
        source="TestRunner",
        data={"goal_id": "GOAL-TEST-01"},
    )
    await bus.publish(test_event)
    await asyncio.sleep(0.01)

    assert len(received) == 1
    assert received[0].data["goal_id"] == "GOAL-TEST-01"
    assert received[0].source == "TestRunner"


@pytest.mark.asyncio
async def test_event_bus_global_subscriber():
    bus = EventBus()
    all_events = []

    def global_handler(event: Event):
        all_events.append(event)

    bus.subscribe_all(global_handler)

    await bus.publish(Event(type=EventType.USER_COMMAND, source="User", data={"text": "hello"}))
    await bus.publish(Event(type=EventType.BATTERY_WARNING, source="HAL", data={"pct": 12}))
    await asyncio.sleep(0.01)

    assert len(all_events) == 2


def test_event_bus_history():
    bus = EventBus(history_limit=5)
    for i in range(10):
        asyncio.run(bus.publish(Event(type=EventType.TELEMETRY_UPDATE, source="Sim", data={"i": i})))

    history = bus.get_recent_events(limit=10)
    assert len(history) == 5
    assert history[-1]["data"]["i"] == 9
