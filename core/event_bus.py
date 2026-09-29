"""
High-Throughput Asynchronous Event Bus for P.H.A.S.S Sphere.
Enables decoupled component communication and live event streaming.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
import uuid
import logging

logger = logging.getLogger("phass.event_bus")


class EventType(str, Enum):
    USER_COMMAND = "USER_COMMAND"
    OBJECT_DETECTED = "OBJECT_DETECTED"
    VOICE_DETECTED = "VOICE_DETECTED"
    GOAL_CREATED = "GOAL_CREATED"
    GOAL_UPDATED = "GOAL_UPDATED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    MEMORY_CREATED = "MEMORY_CREATED"
    LEARNING_EVENT = "LEARNING_EVENT"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    BATTERY_WARNING = "BATTERY_WARNING"
    CONNECTION_CHANGED = "CONNECTION_CHANGED"
    TELEMETRY_UPDATE = "TELEMETRY_UPDATE"
    WORLD_MODEL_UPDATED = "WORLD_MODEL_UPDATED"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    FEEDBACK_RECEIVED = "FEEDBACK_RECEIVED"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass
class Event:
    type: EventType | str
    data: Dict[str, Any]
    source: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, Enum) else str(self.type),
            "source": self.source,
            "timestamp": self.timestamp,
            "data": self.data,
        }


EventHandler = Callable[[Event], Coroutine[Any, Any, None]] | Callable[[Event], None]


class EventBus:
    def __init__(self, history_limit: int = 500):
        self._subscribers: Dict[str, Set[EventHandler]] = {}
        self._global_subscribers: Set[EventHandler] = set()
        self._history: List[Event] = []
        self._history_limit = history_limit
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: EventType | str, handler: EventHandler) -> None:
        key = event_type.value if isinstance(event_type, Enum) else str(event_type)
        if key not in self._subscribers:
            self._subscribers[key] = set()
        self._subscribers[key].add(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        self._global_subscribers.add(handler)

    def unsubscribe(self, event_type: EventType | str, handler: EventHandler) -> None:
        key = event_type.value if isinstance(event_type, Enum) else str(event_type)
        if key in self._subscribers and handler in self._subscribers[key]:
            self._subscribers[key].remove(handler)

    def unsubscribe_all(self, handler: EventHandler) -> None:
        if handler in self._global_subscribers:
            self._global_subscribers.remove(handler)
        for handlers in self._subscribers.values():
            handlers.discard(handler)

    async def publish(self, event: Event) -> None:
        async with self._lock:
            self._history.append(event)
            if len(self._history) > self._history_limit:
                self._history.pop(0)

        key = event.type.value if isinstance(event.type, Enum) else str(event.type)
        handlers_to_call: List[EventHandler] = list(self._global_subscribers)
        if key in self._subscribers:
            handlers_to_call.extend(list(self._subscribers[key]))

        for handler in handlers_to_call:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error executing event handler for {key}: {e}", exc_info=True)

    def get_recent_events(self, limit: int = 50, event_type: Optional[EventType | str] = None) -> List[Dict[str, Any]]:
        target_type = event_type.value if isinstance(event_type, Enum) else (str(event_type) if event_type else None)
        filtered = [
            e.to_dict() for e in self._history
            if target_type is None or (e.type.value if isinstance(e.type, Enum) else str(e.type)) == target_type
        ]
        return filtered[-limit:]

    def clear_history(self) -> None:
        self._history.clear()


# Global Singleton Event Bus instance
event_bus = EventBus()
